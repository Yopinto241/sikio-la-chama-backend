from rest_framework import serializers
from .models import Ilani

class IlaniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ilani
        fields = '__all__'
