from django.db import models

class Leader(models.Model):
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=100)
    description = models.TextField()
    picture = models.ImageField(upload_to='leaders/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name