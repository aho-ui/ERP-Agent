from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("agent", "0002_initial"),
    ]

    operations = [
        migrations.RenameModel("AuditLog", "AgentAction"),
    ]
