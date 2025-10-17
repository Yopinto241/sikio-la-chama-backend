from rest_framework import serializers
from .models import ProblemType

class ProblemTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemType
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['created_at']

    def validate_name(self, value):
        if ProblemType.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Problem type with this name already exists.")
        return value