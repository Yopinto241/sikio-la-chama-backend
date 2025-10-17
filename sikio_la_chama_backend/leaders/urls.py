from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeaderViewSet

router = DefaultRouter()
router.register(r'', LeaderViewSet, basename='leader')

urlpatterns = [
    path('', include(router.urls)),
]