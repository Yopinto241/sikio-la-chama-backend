from django.db import models
from django.contrib.auth.models import AbstractUser
from institutions.models import Institution, Department

class User(AbstractUser):
    device_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    user_type = models.CharField(
        max_length=50,
        choices=[
            ('anonymous', 'Anonymous'),
            ('admin', 'Admin'),
            ('institution_user', 'Institution User'),
            ('department', 'Department User'),
        ],
        default='anonymous'
    )
    phone_number = models.CharField(max_length=15, null=True, blank=True)
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

    def __str__(self):
        return self.username