from django.db import models
from django.conf import settings
from institutions.models import Institution, Department

class Report(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('received', 'Received'),
        ('solving', 'Solving'),
        ('solved', 'Solved'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='reports/', null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    device_id = models.CharField(max_length=255, null=True, blank=True)  # for anonymous users
    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Admin-only fields
    distance_to_admin = models.FloatField(null=True, blank=True)  # in km
    route_info = models.JSONField(null=True, blank=True)  # route steps, map data

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"
