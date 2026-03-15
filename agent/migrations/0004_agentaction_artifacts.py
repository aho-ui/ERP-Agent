from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agent", "0003_rename_auditlog_agentaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="agentaction",
            name="artifacts",
            field=models.JSONField(default=list),
        ),
    ]
