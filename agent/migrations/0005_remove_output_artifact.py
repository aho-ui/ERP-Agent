from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("agent", "0004_agentaction_artifacts"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="agentaction",
            name="output_artifact",
        ),
        migrations.DeleteModel(
            name="OutputArtifact",
        ),
    ]
