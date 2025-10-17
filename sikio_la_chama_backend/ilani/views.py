from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions
from .models import Ilani
from .serializers import IlaniSerializer

class IlaniViewSet(viewsets.ModelViewSet):
    queryset = Ilani.objects.all().order_by('-created_at')
    serializer_class = IlaniSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
