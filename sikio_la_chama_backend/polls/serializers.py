from rest_framework import serializers
from .models import Poll, PollOption, PollVote
from django.db import transaction, models
from django.utils import timezone

class PollOptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False)
    votes_count = serializers.SerializerMethodField()

    class Meta:
        model = PollOption
        fields = ('id', 'text', 'votes_count')

    def get_votes_count(self, obj):
        if obj.poll.show_results or self.context['request'].user.is_staff:
            return obj.votes_count
        return None

class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True)
    options_count = serializers.SerializerMethodField()
    total_voters = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ('id', 'question', 'allow_multiple', 'max_choices', 'start_at', 'end_at', 'options', 'options_count', 'total_voters', 'show_results', 'created_at')
        read_only_fields = ('id', 'created_at', 'total_voters')

    def get_options_count(self, obj):
        return obj.options.count()

    def get_total_voters(self, obj):
        return obj.total_voters()

    def validate(self, data):
        options = data.get('options', [])
        if len(options) < 2:
            raise serializers.ValidationError("A poll must have at least 2 options.")
        if len(options) > 10:
            raise serializers.ValidationError("A poll may have at most 10 options.")
        allow_multiple = data.get('allow_multiple', False)
        max_choices = data.get('max_choices', None)
        if not allow_multiple and max_choices not in (None, 1):
            raise serializers.ValidationError("If allow_multiple is False, max_choices must be omitted or 1.")
        if max_choices is not None:
            if max_choices < 1:
                raise serializers.ValidationError("max_choices must be at least 1.")
            if max_choices >= len(options):
                raise serializers.ValidationError("max_choices must be strictly less than the number of options.")
        return data

    @transaction.atomic
    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        if validated_data.get('max_choices') is None:
            validated_data['max_choices'] = len(options_data) - 1 if validated_data.get('allow_multiple') else 1
        poll = Poll.objects.create(**validated_data)
        for opt in options_data:
            PollOption.objects.create(poll=poll, text=opt['text'])
        return poll

    @transaction.atomic
    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if options_data is not None:
            instance.options.all().delete()
            instance.votes.all().delete()
            for opt in options_data:
                PollOption.objects.create(poll=instance, text=opt['text'])
        return instance

class PollListSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)
    options_count = serializers.SerializerMethodField()
    total_voters = serializers.SerializerMethodField()
    has_voted = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ('id', 'question', 'allow_multiple', 'max_choices', 'start_at', 'end_at', 'options', 'options_count', 'total_voters', 'show_results', 'has_voted', 'created_at')

    def get_options_count(self, obj):
        return obj.options.count()

    def get_total_voters(self, obj):
        return obj.total_voters()

    def get_has_voted(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        user = getattr(request, 'user', None)
        device_id = request.headers.get('DEVICE_ID') or request.headers.get('Device-Id') or request.data.get('device_id')
        if user and user.is_authenticated:
            return obj.votes.filter(user=user).exists()
        elif device_id:
            return obj.votes.filter(device_id=device_id).exists()
        return False

class VoteCreateSerializer(serializers.Serializer):
    option_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate_option_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate option IDs detected.")
        return value

    def validate(self, data):
        poll = self.context['poll']
        option_ids = data['option_ids']
        options = poll.options.filter(id__in=option_ids)
        if options.count() != len(option_ids):
            valid_ids = list(poll.options.values_list('id', flat=True))
            raise serializers.ValidationError(
                f"One or more selected options are invalid for this poll. Valid IDs: {valid_ids}, Provided: {option_ids}"
            )
        if not poll.allow_multiple and len(option_ids) > 1:
            raise serializers.ValidationError("This poll does not allow selecting multiple options.")
        max_choices = poll.max_choices or (1 if not poll.allow_multiple else poll.options.count() - 1)
        if len(option_ids) > max_choices:
            raise serializers.ValidationError(f"You can select at most {max_choices} options.")
        if len(option_ids) >= poll.options.count():
            raise serializers.ValidationError("You cannot select all available options.")
        now = timezone.now()
        if poll.start_at and now < poll.start_at:
            raise serializers.ValidationError("This poll has not started yet.")
        if poll.end_at and now > poll.end_at:
            raise serializers.ValidationError("This poll has already ended.")
        return data

    def create_vote(self, request):
        poll = self.context['poll']
        option_ids = self.validated_data['option_ids']
        user = getattr(request, 'user', None)
        device_id = request.headers.get('DEVICE_ID') or request.headers.get('Device-Id') or request.data.get('device_id')
        if user and user.is_authenticated:
            if poll.votes.filter(user=user).exists():
                raise serializers.ValidationError("User has already voted on this poll.")
        elif device_id:
            if poll.votes.filter(device_id=device_id).exists():
                raise serializers.ValidationError("Device has already voted on this poll.")
        else:
            raise serializers.ValidationError("Anonymous votes require a DEVICE_ID header.")
        
        vote = PollVote.objects.create(
            poll=poll,
            user=user if user and user.is_authenticated else None,
            device_id=device_id if not (user and user.is_authenticated) else None
        )
        selected = poll.options.filter(id__in=option_ids)
        vote.selected_options.set(selected)
        for opt in selected:
            opt.votes_count = models.F('votes_count') + 1
            opt.save()
        for opt in selected:
            opt.refresh_from_db()
        return vote