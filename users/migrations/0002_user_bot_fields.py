import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="api_key",
            field=models.UUIDField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="api_key_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("viewer", "Viewer"),
                    ("operator", "Operator"),
                    ("admin", "Admin"),
                    ("bot", "Bot"),
                ],
                default="viewer",
                max_length=20,
            ),
        ),
    ]
