from django.db import models

class Institution(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Institutions"

    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=100)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='departments')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'institution']
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.name} ({self.institution.name})"

class InstitutionFilePermission(models.Model):
    institution = models.OneToOneField(
        Institution,
        on_delete=models.CASCADE,
        related_name='file_permission'  # Unique related_name to avoid clashes
    )
    allow_file = models.BooleanField(default=False)

    def __str__(self):
        return f"File permission for {self.institution.name}: {self.allow_file}"