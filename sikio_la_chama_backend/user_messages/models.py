from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import User
from institutions.models import Institution, Department
from problem_types.models import ProblemType

class Message(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('answered', 'Answered'),
        ('solved', 'Solved'),
        ('help_received', 'Help Received'),
    )

    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    problem_type = models.ForeignKey(ProblemType, on_delete=models.SET_NULL, null=True, blank=True)
    other_problem = models.CharField(max_length=200, blank=True, null=True)
    content = models.TextField(max_length=1000)
    ward = models.CharField(max_length=100)
    street = models.CharField(max_length=100)
    sub_street = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    file = models.FileField(upload_to="message_files/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)
    reply_count = models.PositiveIntegerField(default=0)

    def clean(self):
        messages_today = Message.objects.filter(
            sender=self.sender, timestamp__date=timezone.now().date()
        ).count()
        if messages_today >= 10:
            raise ValidationError("You can only send 10 messages per day.")
        if self.reply_count >= 10:
            raise ValidationError("Maximum 10 replies per message.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sender.username} to {self.institution.name}: {self.content[:50]}"

class Reply(models.Model):
    message = models.ForeignKey(Message, related_name='replies', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_replies', on_delete=models.CASCADE)
    content = models.TextField(max_length=1000)
    file = models.FileField(upload_to="reply_files/", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.message.reply_count >= 10:
            raise ValidationError("Maximum 10 replies per message.")
        self.message.reply_count += 1
        self.message.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reply by {self.sender.username}: {self.content[:50]}"

class InstitutionFilePermission(models.Model):
    institution = models.OneToOneField(Institution, on_delete=models.CASCADE)
    allow_file = models.BooleanField(default=False)

    def __str__(self):
        return f"File permission for {self.institution.name}: {self.allow_file}"