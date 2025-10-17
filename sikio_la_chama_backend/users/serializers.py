from rest_framework import serializers
from rest_framework.authtoken.models import Token
from .models import User
from institutions.models import Institution, Department

class UserSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField()
    institution = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'user_type',
            'phone_number',
            'device_id',
            'institution',
            'department',
            'token',
        ]
        read_only_fields = ['id', 'token', 'institution', 'department']

    def get_token(self, obj):
        token, created = Token.objects.get_or_create(user=obj)
        return token.key

    def get_institution(self, obj):
        return {"id": obj.institution.id, "name": obj.institution.name} if obj.institution else None

    def get_department(self, obj):
        return {"id": obj.department.id, "name": obj.department.name} if obj.department else None

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    institution = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all(), required=False, allow_null=True
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'username',
            'password',
            'user_type',
            'phone_number',
            'device_id',
            'institution',
            'department',
        ]
    def validate(self, data):
        """Ensure only admins can create elevated users and auto-align department->institution."""
        request = self.context.get('request')
        user_type = data.get('user_type')

        # Only admin/staff users can create institution or department users
        if user_type in ['institution_user', 'department'] and (
            not request or not getattr(request.user, 'is_staff', False)
        ):
            raise serializers.ValidationError({
                'user_type': 'Only admin users can create institution or department users.'
            })

        # If department provided but institution not, inherit institution from department
        if data.get('department') and not data.get('institution'):
            data['institution'] = data['department'].institution

        # Require department/institution when user_type implies it
        if user_type == 'department' and not data.get('department'):
            raise serializers.ValidationError({
                'department': 'A department must be provided when creating a department user.'
            })

        if user_type == 'institution_user' and not data.get('institution'):
            raise serializers.ValidationError({
                'institution': 'An institution must be provided when creating an institution user.'
            })

        # If both provided, ensure consistency: department must belong to institution
        if data.get('department') and data.get('institution'):
            dept_inst = data['department'].institution
            if dept_inst and dept_inst.id != data['institution'].id:
                raise serializers.ValidationError({
                    'department': 'The provided department does not belong to the provided institution.'
                })

        return data

    def create(self, validated_data):
        device_id = validated_data.pop('device_id', None)
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)

        # Fallbacks for anonymous/device-driven creation
        if not device_id:
            device_id = f"anon_{User.objects.count() + 1}"
        if not username:
            username = f"anon_{device_id}"

        user = User.objects.create_user(
            username=username,
            password=password,
            **validated_data
        )
        # Ensure device_id persisted
        user.device_id = device_id
        user.save()
        Token.objects.get_or_create(user=user)
        return user