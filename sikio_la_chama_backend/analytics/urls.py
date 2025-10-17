from django.urls import path
from .views import AdminAnalyticsView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_stats_docs(request):
    return Response({
        'description': 'Admin analytics endpoint',
        'endpoint': '/api/analytics/admin-stats/',
        'query_params': {
            'start': 'ISO date or datetime (inclusive)',
            'end': 'ISO date or datetime (inclusive)',
            'institution': 'filter by institution id',
            'daily': 'true/false -> include daily buckets',
            'per_feed': 'true/false -> include per-feed reaction breakdown',
        }
    })


urlpatterns = [
    path('admin-stats/', AdminAnalyticsView.as_view(), name='admin_analytics'),
    path('admin-stats/docs/', admin_stats_docs, name='admin_analytics_docs'),
]
