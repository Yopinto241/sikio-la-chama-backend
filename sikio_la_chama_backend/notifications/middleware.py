from __future__ import annotations

from typing import Optional

from django.utils.deprecation import MiddlewareMixin

from .models import PushDevice


class PushDeviceAutoRegisterMiddleware(MiddlewareMixin):
    """Auto-register/update push device from headers on any request.

    Frontend can send headers once (on any API call) and avoid a dedicated
    registration endpoint:
      - X-Push-Token: <FCM token>
      - X-Push-Platform: android|ios|web (optional)
    """

    def process_request(self, request):
        token = request.META.get('HTTP_X_PUSH_TOKEN') or request.META.get('HTTP_X_FCM_TOKEN')
        if not token:
            return None

        user = getattr(request, 'user', None)
        if not getattr(user, 'is_authenticated', False):
            # Try DRF token auth ad-hoc so middleware can still work on token auth
            try:
                from rest_framework.authentication import TokenAuthentication

                auth_result = TokenAuthentication().authenticate(request)
                if auth_result:
                    user, _ = auth_result
            except Exception:
                return None

        if getattr(user, 'is_authenticated', False):
            platform = (request.META.get('HTTP_X_PUSH_PLATFORM') or 'android').lower()
            try:
                PushDevice.objects.update_or_create(
                    token=token,
                    defaults={'user': user, 'platform': platform, 'active': True},
                )
            except Exception:
                # Never block the request flow on token upsert errors
                pass

        return None

