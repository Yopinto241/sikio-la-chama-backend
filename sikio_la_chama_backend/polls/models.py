from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

User = settings.AUTH_USER_MODEL

class Poll(models.Model):
    question = models.CharField(max_length=512)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    allow_multiple = models.BooleanField(default=False)
    max_choices = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Max number of choices a user may select (if allow_multiple=True). If null, uses 1 or number_of_options-1."
    )
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    show_results = models.BooleanField(default=False, help_text="Whether vote counts are visible to users.")

    def options_count(self):
        return self.options.count()

    def total_voters(self):
        return self.votes.count()

    def __str__(self):
        return self.question

class PollOption(models.Model):
    poll = models.ForeignKey(Poll, related_name='options', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    votes_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.poll.id}: {self.text}"

class PollVote(models.Model):
    poll = models.ForeignKey(Poll, related_name='votes', on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    selected_options = models.ManyToManyField(PollOption, related_name='selected_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['poll', 'user'], name='unique_poll_user_vote', condition=models.Q(user__isnull=False)),
            models.UniqueConstraint(fields=['poll', 'device_id'], name='unique_poll_device_vote', condition=models.Q(device_id__isnull=False)),
        ]

    def __str__(self):
        who = self.user or self.device_id
        return f"Vote by {who} on poll {self.poll_id}"