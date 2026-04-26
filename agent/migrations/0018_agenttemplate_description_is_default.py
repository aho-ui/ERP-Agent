from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0017_slack_platform'),
    ]

    operations = [
        migrations.AddField(
            model_name='agenttemplate',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='agenttemplate',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
    ]
