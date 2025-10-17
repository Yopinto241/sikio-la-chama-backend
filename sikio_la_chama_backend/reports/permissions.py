from rest_framework import permissions
from users.models import User
import logging

logger = logging.getLogger(__name__)


class DeviceIdPermission(permissions.BasePermission):
    """
    Allow access if DEVICE_ID header is provided for anonymous/device-based requests.
    If the request is already authenticated, allow it through.
    Auto-create anonymous user if not exists when a DEVICE_ID header is present.
    """
    def has_permission(self, request, view):
        # If request is already authenticated (e.g., Token auth), allow it.
        if getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False):
            logger.debug(
                "DeviceIdPermission: request already authenticated -> user=%s, path=%s, method=%s",
                getattr(request.user, 'username', None),
                getattr(request, 'path', None),
                getattr(request, 'method', None),
            )
            return True

        # Try a few common header name variations (headers are case-insensitive via request.headers)
        # Also check request.data and query params as a fallback while debugging.
        candidates = [
            'DEVICE_ID', 'Device-Id', 'Device-ID', 'X-Device-ID', 'x-device-id'
        ]
        device_id = None
        found_in = None

        # Check request.headers first
        try:
            for name in candidates:
                val = request.headers.get(name)
                if val:
                    device_id = val
                    found_in = f'header:{name}'
                    break
        except Exception:
            # Some WSGI setups may not provide request.headers; ignore and continue
            logger.exception('DeviceIdPermission: error reading request.headers')

        # Check META (raw HTTP_ headers)
        if not device_id:
            try:
                for name in candidates:
                    meta_name = 'HTTP_' + name.upper().replace('-', '_')
                    val = request.META.get(meta_name)
                    if val:
                        device_id = val
                        found_in = f'meta:{meta_name}'
                        break
            except Exception:
                logger.exception('DeviceIdPermission: error reading request.META')

        # Fallback: check request.data (POST body) and query params
        if not device_id:
            try:
                data_val = getattr(request, 'data', {}) and request.data.get('device_id')
                if data_val:
                    device_id = data_val
                    found_in = 'body:device_id'
            except Exception:
                logger.exception('DeviceIdPermission: error reading request.data')

        if not device_id:
            try:
                q_val = getattr(request, 'query_params', {}) and request.query_params.get('device_id')
                if q_val:
                    device_id = q_val
                    found_in = 'query:device_id'
            except Exception:
                logger.exception('DeviceIdPermission: error reading request.query_params')

        logger.debug('DeviceIdPermission: path=%s method=%s found_in=%s device_id=%s',
                     getattr(request, 'path', None), getattr(request, 'method', None), found_in, device_id)

        if not device_id:
            # Extra debug output: dump a few useful request.META keys to help diagnose missing headers
            try:
                meta_sample = {k: v for k, v in request.META.items() if k.startswith('HTTP_') or k in ('CONTENT_TYPE', 'CONTENT_LENGTH')}
            except Exception:
                meta_sample = 'unavailable'
            logger.debug('DeviceIdPermission: missing device_id; request.META sample=%s', meta_sample)
            return False  # Reject requests without device ID when not authenticated

        # Attach or create a user based on device_id for anonymous/device-driven access
        try:
            user = User.objects.filter(device_id=device_id).first()
        except Exception:
            logger.exception('DeviceIdPermission: database error when querying User')
            return False

        if user:
            logger.debug('DeviceIdPermission: found user id=%s username=%s for device_id=%s', user.id, user.username, device_id)
        else:
            try:
                logger.info('DeviceIdPermission: Creating anonymous user for device_id=%s', device_id)
                user = User.objects.create(
                    username=f"anon_{device_id[:8]}",
                    device_id=device_id,
                    user_type="anonymous"
                )
                logger.debug('DeviceIdPermission: created user id=%s username=%s', user.id, user.username)
            except Exception:
                logger.exception('DeviceIdPermission: failed to create anonymous user for device_id=%s', device_id)
                return False

        # Attach the resolved/created user to request so downstream code can use it
        request.user = user
        logger.debug('DeviceIdPermission: attached user=%s to request', getattr(user, 'username', None))
        return True

    def has_object_permission(self, request, view, obj):
        user = getattr(request, 'user', None)
        if not user:
            logger.debug('DeviceIdPermission.has_object_permission: no user attached, denying access')
            return False

        # Admin can see all
        if user.user_type == 'admin':
            logger.debug('DeviceIdPermission.has_object_permission: admin user, allow')
            return True

        # Institution user sees reports for their institution
        if user.user_type == 'institution_user' and obj.institution == getattr(user, 'institution', None):
            return True

        # Department user sees reports for their department
        if user.user_type == 'department' and obj.department == getattr(user, 'department', None):
            return True

        # Anonymous/device user sees their own reports
        if obj.device_id == getattr(user, 'device_id', None):
            logger.debug('DeviceIdPermission.has_object_permission: device match allow (obj.device_id=%s user.device_id=%s)', obj.device_id, getattr(user, 'device_id', None))
            return True

        return False
