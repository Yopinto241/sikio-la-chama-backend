from rest_framework import serializers
from .models import Report
from users.serializers import UserSerializer

# 1️⃣ Create report (anonymous/device)
class CreateReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['title', 'description', 'image', 'latitude', 'longitude',
                  'device_id', 'institution', 'department']

# 2️⃣ Fetch report (shared)
class ReportSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'title', 'description', 'image', 'latitude', 'longitude',
                  'user', 'device_id', 'institution', 'department',
                  'status', 'created_at', 'updated_at', 'distance_to_admin', 'route_info']

# 3️⃣ Admin-only: update status
class ReportStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'status', 'distance_to_admin', 'route_info']
        read_only_fields = ['distance_to_admin', 'route_info']
