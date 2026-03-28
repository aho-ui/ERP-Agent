import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0010_bot_instance'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='botinstance',
            name='role',
            field=models.CharField(
                choices=[('viewer', 'Viewer'), ('admin', 'Admin')],
                default='viewer',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='chatsession',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='chat_sessions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='bot',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sessions',
                to='agent.botinstance',
            ),
        ),
    ]
