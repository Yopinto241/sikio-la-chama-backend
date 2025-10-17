from django.db import models
from users.models import User
from institutions.models import Institution

class Feed(models.Model):
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feeds')
    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    description = models.TextField()
    image = models.ImageField(upload_to='feeds/images/', null=True, blank=True)
    # New: allow admin to attach a video to a feed
    video = models.FileField(upload_to='feeds/videos/', null=True, blank=True)
    # New: optional link that admin can include in the description
    link = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    impressions = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feed by {self.posted_by.username} at {self.created_at}"


class FeedShare(models.Model):
    """Represents a user sharing a feed (can be by authenticated user or anonymous via device_id).

    We keep a reference to the User when available, otherwise the share can be created
    for an anonymous user created elsewhere (views create anon users by device_id).
    """
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_shares')
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} shared Feed {self.feed.id} at {self.created_at}"

class FeedReaction(models.Model):
    REACTION_CHOICES = (
        ('like', 'Like'),
        ('love', 'Love'),
        ('cry', 'Cry'),
        ('smile', 'Smile'),
    )
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_reactions')
    reaction_type = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('feed', 'user')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} {self.reaction_type} on Feed {self.feed.id}"