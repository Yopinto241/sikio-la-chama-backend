from rest_framework import serializers
from .models import Institution, Department

class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ['id', 'name', 'description', 'created_at']  # Added 'id' for full response
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        if Institution.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Institution with this name already exists.")
        return value

class DepartmentSerializer(serializers.ModelSerializer):
    institution = serializers.PrimaryKeyRelatedField(queryset=Institution.objects.all())  # For create/update, use ID

    class Meta:
        model = Department
        fields = ['id', 'name', 'institution', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        institution = self.initial_data.get('institution')
        if Department.objects.filter(name__iexact=value, institution=institution).exists():
            raise serializers.ValidationError("Department with this name already exists in the selected institution.")
        return value