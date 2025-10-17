from rest_framework import serializers
from .models import Leader

class LeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leader
        fields = ['id', 'name', 'role', 'description', 'picture', 'created_at']
        read_only_fields = ['id', 'created_at']