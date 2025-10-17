from rest_framework import serializers
from .models import Message, Reply, InstitutionFilePermission
from users.serializers import UserSerializer
from institutions.models import Institution, Department
from problem_types.models import ProblemType

# 20 MB max
MAX_UPLOAD_SIZE = 20 * 1024 * 1024

class ReplySerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    file = serializers.FileField(required=False, allow_null=True)
    # helpful flags for frontend
    is_sender = serializers.SerializerMethodField(read_only=True)
    is_staff = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Reply
        fields = ['id', 'sender', 'content', 'file', 'timestamp', 'is_sender', 'is_staff']
        read_only_fields = ['id', 'timestamp', 'is_sender', 'is_staff']

    def get_is_sender(self, obj):
        request = self.context.get('request')
        device_user = self.context.get('device_user')
        current_user = None
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            current_user = request.user
        elif device_user:
            current_user = device_user
        return current_user == obj.sender

    def get_is_staff(self, obj):
        return getattr(obj.sender, 'user_type', None) in ['admin', 'institution_user', 'department']

    def validate_file(self, value):
        if not value:
            return value
        if value.size > MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(f"File too large. Size should not exceed {MAX_UPLOAD_SIZE} bytes.")
        return value

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    # Replies will be filtered per-request (sender sees admin/institution replies;
    # staff sees replies for their scope). We use a SerializerMethodField
    # so we can access the request context.
    replies = serializers.SerializerMethodField()
    file = serializers.FileField(required=False, allow_null=True)
    institution = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all(), write_only=True
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), write_only=True
    )
    problem_type = serializers.PrimaryKeyRelatedField(
        queryset=ProblemType.objects.all(), write_only=True, required=False, allow_null=True
    )
    institution_detail = serializers.SerializerMethodField(read_only=True)
    department_detail = serializers.SerializerMethodField(read_only=True)
    ward = serializers.CharField(required=True)
    street = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    content = serializers.CharField(required=True)
    other_problem = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Message
        fields = [
            'id', 'sender',
            'institution', 'institution_detail',
            'department', 'department_detail',
            'problem_type', 'other_problem',
            'content', 'ward', 'street', 'phone_number',
            'status', 'file', 'timestamp', 'replies'
        ]
        read_only_fields = [
            'id', 'timestamp', 'replies', 'status',
            'institution_detail', 'department_detail'
        ]

    def get_institution_detail(self, obj):
        return {"id": obj.institution.id, "name": obj.institution.name} if obj.institution else None

    def get_department_detail(self, obj):
        return {"id": obj.department.id, "name": obj.department.name} if obj.department else None

    def validate(self, data):
        if not data.get('problem_type') and not data.get('other_problem'):
            raise serializers.ValidationError(
                {"problem_type": "Select a problem type or provide other_problem."}
            )
        return data

    def validate_file(self, value):
        if not value:
            return value
        if value.size > MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(f"File too large. Size should not exceed {MAX_UPLOAD_SIZE} bytes.")
        return value

    def create(self, validated_data):
        return Message.objects.create(**validated_data)

    def get_replies(self, obj):
        """Return replies filtered according to the requesting user.

        Rules implemented:
        - If the requester is the message sender (including anonymous sender
          identified via device_id), return only replies sent by admin/
          institution/department users (these are the authoritative replies).
        - If the requester is an admin/institution_user/department user and
          the message belongs to their scope (institution/department), return
          all replies for moderation/handling purposes.
        - Otherwise, return an empty list.
        """
        request = self.context.get('request')
        device_user = self.context.get('device_user')
        current_user = None
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            current_user = request.user
        elif device_user:
            current_user = device_user

        if not current_user:
            return []

        # Message sender: show both their own replies and authoritative replies
        if current_user == obj.sender:
            from django.db.models import Q
            replies_qs = obj.replies.filter(
                Q(sender=obj.sender) | Q(sender__user_type__in=['admin', 'institution_user', 'department'])
            )
            return ReplySerializer(replies_qs, many=True, context=self.context).data

        # Staff views: ensure they belong to the same scope
        if getattr(current_user, 'user_type', None) in ['admin', 'institution_user', 'department']:
            if current_user.user_type == 'department' and current_user.department != obj.department:
                return []
            if current_user.user_type == 'institution_user' and current_user.institution != obj.institution:
                return []
            # admin can see everything
            replies_qs = obj.replies.all()
            return ReplySerializer(replies_qs, many=True, context=self.context).data

        return []

class InstitutionFilePermissionSerializer(serializers.ModelSerializer):
    # expose institution_id as a read-only integer sourced from the related institution
    institution_id = serializers.IntegerField(source='institution.id', read_only=True)

    class Meta:
        model = InstitutionFilePermission
        fields = ['institution_id', 'allow_file']