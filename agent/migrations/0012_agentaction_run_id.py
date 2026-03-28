from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0011_bot_role_session_bot'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentaction',
            name='run_id',
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
    ]
