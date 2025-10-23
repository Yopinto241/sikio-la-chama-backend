import json
import logging
from typing import Iterable, Dict, Any, List, Optional, Tuple

import requests
from django.conf import settings

try:
    import google.auth.transport.requests
    from google.oauth2 import service_account
    _HAS_GOOGLE_AUTH = True
except Exception:  # pragma: no cover
    _HAS_GOOGLE_AUTH = False

from .models import PushDevice

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


def _get_sa_credentials() -> Optional[Tuple[str, str]]:
    """Return (access_token, project_id) if v1 credentials are configured and usable."""
    if not _HAS_GOOGLE_AUTH:
        return None
    json_blob = getattr(settings, 'FIREBASE_CREDENTIALS_JSON', None)
    path = getattr(settings, 'FIREBASE_CREDENTIALS_FILE', None)
    try:
        if json_blob:
            info = json.loads(json_blob)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        elif path:
            creds = service_account.Credentials.from_service_account_file(str(path), scopes=SCOPES)
        else:
            return None
        req = google.auth.transport.requests.Request()
        creds.refresh(req)
        return creds.token, creds.project_id
    except Exception as exc:
        logger.warning('FCM v1 credentials not usable: %s', exc)
        return None


def _send_v1(token: str, title: str, body: str, data: Dict[str, Any] | None) -> None:
    sa = _get_sa_credentials()
    if not sa:
        return
    access_token, project_id = sa
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data_only = getattr(settings, 'NOTIFICATIONS_DATA_ONLY', False)
    message: Dict[str, Any] = {"token": token, "data": data or {}}
    if not data_only:
        message["notification"] = {"title": title, "body": body}
    payload = {"message": message}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=5)
        if r.status_code not in (200, 201):
            logger.warning('FCM v1 send failed (%s): %s', r.status_code, r.text)
    except Exception as exc:
        logger.warning('FCM v1 request error: %s', exc)


def _send_legacy(tokens: List[str], title: str, body: str, data: Dict[str, Any] | None) -> None:
    key = getattr(settings, 'FCM_SERVER_KEY', None)
    if not key or not tokens:
        return
    url = 'https://fcm.googleapis.com/fcm/send'
    headers = {'Content-Type': 'application/json', 'Authorization': f'key={key}'}
    data_only = getattr(settings, 'NOTIFICATIONS_DATA_ONLY', False)
    payload: Dict[str, Any] = {
        'registration_ids': tokens[:1000],
        'data': data or {},
        'android': {'priority': 'high'},
        'apns': {'headers': {'apns-priority': '10'}},
    }
    if not data_only:
        payload['notification'] = {'title': title, 'body': body}
    try:
        requests.post(url, json=payload, headers=headers, timeout=5)
    except Exception as exc:
        logger.info('FCM legacy send failed: %s', exc)


def send_push_to_tokens(tokens: List[str], title: str, body: str, data: Dict[str, Any] | None = None) -> None:
    if not tokens:
        return
    # Prefer v1; fallback to legacy batch send if v1 not configured
    if _get_sa_credentials():
        for t in tokens:
            _send_v1(t, title, body, data)
    else:
        _send_legacy(tokens, title, body, data)


def send_push_to_users(user_ids: Iterable[int], title: str, body: str, data: Dict[str, Any] | None = None) -> None:
    tokens = list(PushDevice.objects.filter(user_id__in=list(user_ids), active=True).values_list('token', flat=True))
    if not tokens:
        return
    for i in range(0, len(tokens), 1000):
        send_push_to_tokens(tokens[i:i + 1000], title, body, data)
