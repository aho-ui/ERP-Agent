import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0012_agentaction_run_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentaction',
            name='source',
            field=models.CharField(
                choices=[('web', 'Web'), ('discord', 'Discord'), ('telegram', 'Telegram'), ('system', 'System')],
                default='web',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='agentaction',
            name='bot',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='actions',
                to='agent.botinstance',
            ),
        ),
    ]
