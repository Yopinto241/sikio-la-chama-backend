from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IlaniViewSet

router = DefaultRouter()
router.register(r'ilani', IlaniViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
