import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0015_whatsapp_platform'),
    ]

    operations = [
        migrations.CreateModel(
            name='BotMedia',
            fields=[
                ('key', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('data', models.BinaryField()),
                ('content_type', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
