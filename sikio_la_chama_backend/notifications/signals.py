from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from users.models import User
from announcements.models import Announcement
from feeds.models import Feed
from polls.models import Poll
from user_messages.models import Reply

from .models import Notification
from .push import send_push_to_users


def _notify_users(user_qs, title: str, body: str, obj, ntype: str):
    users = list(user_qs.values_list('id', flat=True))
    if not users:
        return
    # Bulk create Notifications
    ct = ContentType.objects.get_for_model(obj.__class__)
    notifs = [
        Notification(
            recipient_id=uid,
            title=title,
            body=body,
            type=ntype,
            content_type=ct,
            object_id=obj.pk,
        )
        for uid in users
    ]
    Notification.objects.bulk_create(notifs, ignore_conflicts=True)
    # Send push
    send_push_to_users(users, title, body, data={'type': ntype, 'object_id': obj.pk})


@receiver(post_save, sender=Announcement)
def on_announcement_created(sender, instance: Announcement, created, **kwargs):
    if not created:
        return
    title = instance.title
    body = (instance.description or '')[:120]
    # Notify all non-admin users
    user_qs = User.objects.exclude(user_type='admin')
    _notify_users(user_qs, title, body, instance, 'announcement')


@receiver(post_save, sender=Feed)
def on_feed_created(sender, instance: Feed, created, **kwargs):
    if not created:
        return
    title = 'New Feed'
    body = (instance.description or '')[:120]
    if instance.institution_id:
        user_qs = User.objects.exclude(user_type='admin').filter(institution_id=instance.institution_id)
    else:
        user_qs = User.objects.exclude(user_type='admin')
    _notify_users(user_qs, title, body, instance, 'feed')


@receiver(post_save, sender=Poll)
def on_poll_created(sender, instance: Poll, created, **kwargs):
    if not created:
        return
    title = 'New Poll'
    body = instance.question[:120]
    user_qs = User.objects.exclude(user_type='admin')
    _notify_users(user_qs, title, body, instance, 'poll')


@receiver(post_save, sender=Reply)
def on_reply_created(sender, instance: Reply, created, **kwargs):
    if not created:
        return
    # Notify original message sender, if different from replier
    recipient = instance.message.sender
    if recipient_id := getattr(recipient, 'id', None):
        if recipient_id != instance.sender_id:
            title = 'Your message has a reply'
            body = (instance.content or '')[:120]
            _notify_users(User.objects.filter(id=recipient_id), title, body, instance, 'message_reply')

