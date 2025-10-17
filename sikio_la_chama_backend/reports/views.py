from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.mail import send_mail
from .models import Report
from .serializers import ReportSerializer, CreateReportSerializer, ReportStatusSerializer
from .permissions import DeviceIdPermission
from rest_framework.decorators import api_view
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()

    def get_queryset(self):
        """Return a queryset scoped to the requesting user's permissions.

        - admin: all reports
        - institution_user: reports for their institution
        - department: reports for their department
        - anonymous/device user: reports created from the same device_id
        """
        qs = Report.objects.all().order_by('-created_at')
        request = getattr(self, 'request', None)
        user = getattr(request, 'user', None) if request is not None else None

        # Safety: if no user attached, return empty queryset
        if not user:
            return Report.objects.none()

        # Admins see everything
        if getattr(user, 'is_authenticated', False) and getattr(user, 'user_type', None) == 'admin':
            return qs

        # Institution users
        if getattr(user, 'user_type', None) == 'institution_user' and getattr(user, 'institution', None):
            return qs.filter(institution=user.institution)

        # Department users
        if getattr(user, 'user_type', None) == 'department' and getattr(user, 'department', None):
            return qs.filter(department=user.department)

        # Anonymous/device users — scope by device_id
        device_id = getattr(user, 'device_id', None)
        if device_id:
            return qs.filter(device_id=device_id)

        return Report.objects.none()

    def get_permissions(self):
        """
        Permissions:
        - create: anyone (DEVICE_ID header allowed)
        - list/retrieve: DEVICE_ID header required
        - update_status: admin only
        """
        if self.action == 'create':
            # Use DeviceIdPermission for create so requests that provide a device id
            # can be authenticated/attached as an anonymous device user.
            return [DeviceIdPermission()]
        if self.action in ['list', 'retrieve']:
            return [DeviceIdPermission()]
        if self.action == 'update_status':
            return [permissions.IsAuthenticated()]
        return [DeviceIdPermission()]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateReportSerializer
        if self.action == 'update_status':
            return ReportStatusSerializer
        return ReportSerializer

    def perform_create(self, serializer):
        user = getattr(self.request, 'user', None)
        serializer.save(user=user, device_id=getattr(user, 'device_id', None))

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def update_status(self, request, pk=None):
        """
        Admin/Institution updates status, adds distance/route info, and notifies reporter.
        """
        report = self.get_object()
        serializer = ReportStatusSerializer(report, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if report.user and report.user.email:
                send_mail(
                    subject="Report status updated",
                    message=f"Your report '{report.title}' status is now {report.status}",
                    from_email="noreply@example.com",
                    recipient_list=[report.user.email],
                )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_report_route(request, pk):
    """Fetch driving route from admin coords (passed as query params) to report location using MapTiler.

    Query params: admin_lat, admin_lng
    """
    admin_lat = request.GET.get('admin_lat')
    admin_lng = request.GET.get('admin_lng')

    if not admin_lat or not admin_lng:
        return Response({'error': 'Missing admin coordinates (admin_lat, admin_lng required)'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

    # Ensure MapTiler API key is available
    api_key = getattr(settings, 'MAPTILER_API_KEY', None)
    if not api_key:
        logger.error('MapTiler API key missing in settings')
        return Response({'error': 'MapTiler API key not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Validate report coordinates
    if report.longitude is None or report.latitude is None:
        return Response({'error': 'Report missing coordinates'}, status=status.HTTP_400_BAD_REQUEST)

    # MapTiler routes v2 expects lon,lat pairs and uses /routes/v2/{profile}/{coords}
    # Use geojson geometries and full overview for best results.
    url = (
        f"https://api.maptiler.com/routes/v2/driving/{admin_lng},{admin_lat};"
        f"{report.longitude},{report.latitude}?key={api_key}&overview=full&geometries=geojson"
    )
    logger.debug('Requesting MapTiler route url=%s', url)

    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        logger.exception('MapTiler request failed')
        # Try alternate MapTiler endpoint used by the mobile client
        alt_url = (
            f"https://api.maptiler.com/routing/route/geojson?key={api_key}"
            f"&start={admin_lng},{admin_lat}&end={report.longitude},{report.latitude}&profile=driving&overview=full"
        )
        logger.debug('Attempting alternate MapTiler endpoint url=%s', alt_url)
        try:
            resp = requests.get(alt_url, timeout=10)
        except requests.RequestException as e2:
            logger.exception('Alternate MapTiler request also failed')
            return Response({'error': 'MapTiler request failed', 'details': str(e2)}, status=status.HTTP_502_BAD_GATEWAY)

    if resp.status_code == 200:
        try:
            data = resp.json()
        except Exception:
            logger.exception('Failed to parse MapTiler JSON')
            return Response({'error': 'Invalid JSON from MapTiler'}, status=status.HTTP_502_BAD_GATEWAY)

        # MapTiler v2 typically returns a dict with a 'routes' list containing
        # distance (meters) and a 'geometry' (GeoJSON). But alternate endpoints
        # or edge cases may return different shapes (ints, nested dicts, or
        # feature collections). Be defensive when parsing to avoid type errors.
        distance_km = None
        route_geojson = None
        try:
            routes = data.get('routes') if isinstance(data, dict) else None

            if isinstance(routes, list) and len(routes) > 0 and isinstance(routes[0], dict):
                first = routes[0]
                distance_m = first.get('distance')
                if distance_m is not None:
                    try:
                        distance_km = float(distance_m) / 1000.0
                    except (TypeError, ValueError):
                        logger.warning('Unable to parse distance value from MapTiler: %r', distance_m)
                # geometry may be present as 'geometry' (GeoJSON) or under 'legs'
                route_geojson = first.get('geometry') or first.get('legs')
            else:
                # Try to support alternate response shapes such as a FeatureCollection
                # or responses where distance is nested under 'summary' or feature properties.
                if isinstance(data, dict):
                    # FeatureCollection-style
                    features = data.get('features')
                    if isinstance(features, list) and len(features) > 0 and isinstance(features[0], dict):
                        feat = features[0]
                        route_geojson = feat.get('geometry') or feat.get('properties', {}).get('geometry')
                        props = feat.get('properties') or {}
                        if 'distance' in props:
                            try:
                                distance_km = float(props.get('distance')) / 1000.0
                            except (TypeError, ValueError):
                                logger.warning('Unable to parse distance from feature properties: %r', props.get('distance'))
                    # summary-based response
                    elif isinstance(data.get('summary'), dict):
                        summary = data.get('summary')
                        dist = summary.get('distance')
                        if dist is not None:
                            try:
                                distance_km = float(dist) / 1000.0
                            except (TypeError, ValueError):
                                logger.warning('Unable to parse summary.distance from MapTiler: %r', dist)
        except Exception:
            logger.exception('Error extracting route/distance from MapTiler response')

        # Return a compact object the client expects: { distance: <km>, route: <geojson>, raw: <maptiler> }
        return Response({'distance': distance_km, 'route': route_geojson, 'raw': data}, status=status.HTTP_200_OK)
    elif resp.status_code == 404:
        # 404 from MapTiler commonly means no route found for the given coordinates.
        # Return 200 with null route/distance so clients handle it gracefully instead of raising an exception.
        logger.warning('MapTiler route not found between admin and report; body=%s', resp.text)
        sanitized = url.replace(f'key={api_key}', 'key=REDACTED')
        return Response({
            'distance': None,
            'route': None,
            'message': 'No route could be found between the given points.',
            'maptiler_url': sanitized
        }, status=status.HTTP_200_OK)
    else:
        logger.error('MapTiler routing returned status=%s body=%s', resp.status_code, resp.text)
        sanitized = url.replace(f'key={api_key}', 'key=REDACTED')
        return Response({'error': 'MapTiler routing failed', 'maptiler_url': sanitized, 'details': resp.text}, status=resp.status_code)
