from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend  # For filtering
from .models import Institution, Department
from .serializers import InstitutionSerializer, DepartmentSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from user_messages.models import InstitutionFilePermission
from user_messages.serializers import InstitutionFilePermissionSerializer
import logging

logger = logging.getLogger(__name__)

# ViewSet for GET /institutions/, read-only for lists.
class InstitutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Matches your settings
    filter_backends = [DjangoFilterBackend]  # Enable filtering
    filterset_fields = ['name']  # e.g., ?name=Police

# ViewSet for GET /institutions/departments/, read-only for lists.
class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Matches your settings
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['institution', 'name']  # e.g., ?institution=1&name=Crime

    def get_queryset(self):
        queryset = super().get_queryset()
        # Support both nested route `institution_pk` (when using nested routers)
        # and the `institution` query parameter.
        institution_id = (
            self.kwargs.get('institution_pk') or
            self.request.query_params.get('institution')
        )

        if institution_id:
            queryset = queryset.filter(institution_id=institution_id)
        return queryset


class InstitutionFilePermissionsView(APIView):
    # Allow any authenticated user to read permissions, only admin can modify.
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        from rest_framework.permissions import IsAdminUser
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get(self, request):
        logger.debug(f"User {request.user} fetching file permissions (institutions scope)")
        permissions = InstitutionFilePermission.objects.all()
        return Response([
            {'institution_id': p.institution.id, 'allow_file': p.allow_file}
            for p in permissions
        ], status=status.HTTP_200_OK)


class InstitutionFilePermissionDetailView(APIView):
    # GET allowed for authenticated users; PATCH restricted to admins
    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        from rest_framework.permissions import IsAdminUser
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get(self, request, institution_id):
        logger.debug(f"User {request.user} fetching file permission for institution {institution_id}")
        permission = InstitutionFilePermission.objects.filter(institution_id=institution_id).first()
        if not permission:
            return Response({'institution_id': institution_id, 'allow_file': False}, status=status.HTTP_200_OK)
        return Response({'institution_id': institution_id, 'allow_file': permission.allow_file}, status=status.HTTP_200_OK)

    def patch(self, request, institution_id):
        logger.debug(f"User {request.user} updating file permission for institution {institution_id}")
        logger.debug(f"Request content_type={request.content_type} data={request.data}")
        permission, _ = InstitutionFilePermission.objects.get_or_create(institution_id=institution_id, defaults={'allow_file': False})
        allow_keys = ['allow_file', 'allow', 'allowFile', 'allow_files']
        allow_present = False
        allow = None
        found_key = None
        for k in allow_keys:
            if k in request.data:
                allow = request.data.get(k)
                allow_present = True
                found_key = k
                break
        logger.debug(f"Found allow key={found_key} present={allow_present} raw_value={allow}")
        if not allow_present:
            logger.warning(f"No allow flag provided when patching permission for institution {institution_id}")
            return Response({'errors': {'allow_file': 'This field is required'}}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(allow, str):
            allow = allow.lower() in ['1', 'true', 'yes', 'on']
        permission.allow_file = bool(allow)
        logger.debug(f"Computed allow={permission.allow_file} (from raw {allow})")
        permission.save()
        return Response({'institution_id': institution_id, 'allow_file': permission.allow_file}, status=status.HTTP_200_OK)

    def put(self, request, institution_id):
        """Replace the permission resource for the institution (PUT semantics).

        For this simple resource the behavior mirrors PATCH, but we accept
        a full representation and return the updated object.
        """
        logger.debug(f"User {request.user} replacing file permission for institution {institution_id} via PUT")
        # Ensure the permission object exists
        permission, _ = InstitutionFilePermission.objects.get_or_create(
            institution_id=institution_id, defaults={'allow_file': False}
        )
        logger.debug(f"Request content_type={request.content_type} data={request.data}")
        # Interpret allow_file from payload; require explicit flag for PUT
        allow_keys = ['allow_file', 'allow', 'allowFile', 'allow_files']
        allow_present = False
        allow = None
        found_key = None
        for k in allow_keys:
            if k in request.data:
                allow = request.data.get(k)
                allow_present = True
                found_key = k
                break
        logger.debug(f"Found allow key={found_key} present={allow_present} raw_value={allow}")
        if not allow_present:
            logger.warning(f"No allow flag provided when putting permission for institution {institution_id}")
            return Response({'errors': {'allow_file': 'This field is required'}}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(allow, str):
            allow = allow.lower() in ['1', 'true', 'yes', 'on']
        permission.allow_file = bool(allow)
        logger.debug(f"Computed allow={permission.allow_file} (from raw {allow})")
        permission.save()
        return Response({'institution_id': institution_id, 'allow_file': permission.allow_file}, status=status.HTTP_200_OK)


class InstitutionFilePermissionViewSet(viewsets.ViewSet):
    """Expose institution-scoped file-permissions via the nested router.

    URLs produced by the nested router will include `institution_pk` in kwargs.
    This ViewSet supports list (for a specific institution or all) and
    partial_update to change the `allow_file` flag.
    """
    permission_classes = [IsAdminUser]

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        from rest_framework.permissions import IsAdminUser
        # allow authenticated users to view/list; only admins can partial_update
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def list(self, request, institution_pk=None):
        if institution_pk:
            perm = InstitutionFilePermission.objects.filter(institution_id=institution_pk).first()
            if not perm:
                return Response({'institution_id': institution_pk, 'allow_file': False}, status=status.HTTP_200_OK)
            serializer = InstitutionFilePermissionSerializer(perm)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # no institution_pk: return all
        perms = InstitutionFilePermission.objects.all()
        serializer = InstitutionFilePermissionSerializer(perms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, institution_pk=None, pk=None):
        # ignore pk: update by institution_pk
        if not institution_pk:
            return Response({'detail': 'institution_pk required'}, status=status.HTTP_400_BAD_REQUEST)
        permission, _ = InstitutionFilePermission.objects.get_or_create(institution_id=institution_pk, defaults={'allow_file': False})
        allow_keys = ['allow_file', 'allow', 'allowFile', 'allow_files']
        allow_present = False
        allow = None
        for k in allow_keys:
            if k in request.data:
                allow = request.data.get(k)
                allow_present = True
                break
        if not allow_present:
            logger.warning(f"No allow flag provided when partially updating permission for institution {institution_pk}")
            return Response({'errors': {'allow_file': 'This field is required'}}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(allow, str):
            allow = allow.lower() in ['1', 'true', 'yes', 'on']
        permission.allow_file = bool(allow)
        permission.save()
        serializer = InstitutionFilePermissionSerializer(permission)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ToggleFilePermissionView(APIView):
    """Toggle the allow_file flag for an institution. This endpoint is
    intentionally simple for admin UIs that just flip the permission.

    POST /institutions/<id>/file-permissions/toggle/
    """
    permission_classes = [IsAdminUser]

    def post(self, request, institution_id):
        logger.debug(f"User {request.user} toggling file permission for institution {institution_id}")
        permission, _ = InstitutionFilePermission.objects.get_or_create(
            institution_id=institution_id, defaults={'allow_file': False}
        )
        permission.allow_file = not permission.allow_file
        permission.save()
        logger.info(f"Toggled file permission for institution {institution_id} to {permission.allow_file} by {request.user}")
        return Response({'institution_id': institution_id, 'allow_file': permission.allow_file}, status=status.HTTP_200_OK)


class InstitutionCreateView(APIView):
    """Allow admins to create Institutions via POST.

    POST payload: {"name": "Name", "description": "optional"}
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = InstitutionSerializer(data=request.data)
        if serializer.is_valid():
            institution = serializer.save()
            logger.info(f"Institution {institution.id} created by {request.user}")
            return Response(InstitutionSerializer(institution).data, status=status.HTTP_201_CREATED)
        logger.error(f"Institution creation failed: {serializer.errors}")
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class DepartmentCreateView(APIView):
    """Allow admins to create Departments under an institution via POST.

    POST payload: {"name": "Department Name", "description": "optional"}
    URL: /institutions/<institution_id>/departments/create/
    """
    permission_classes = [IsAdminUser]

    def post(self, request, institution_id):
        data = request.data.copy()
        data['institution'] = institution_id
        serializer = DepartmentSerializer(data=data)
        if serializer.is_valid():
            department = serializer.save()
            logger.info(f"Department {department.id} created under institution {institution_id} by {request.user}")
            return Response(DepartmentSerializer(department).data, status=status.HTTP_201_CREATED)
        logger.error(f"Department creation failed for institution {institution_id}: {serializer.errors}")
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)