from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='notification',
            constraint=models.UniqueConstraint(
                fields=('recipient', 'type', 'content_type', 'object_id'),
                name='unique_notification_per_object',
            ),
        ),
    ]

