from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, get_report_route

router = DefaultRouter()
router.register(r'', ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
    path('<int:pk>/route/', get_report_route, name='report-route'),
]
