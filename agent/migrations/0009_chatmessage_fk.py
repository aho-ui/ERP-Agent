from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("agent", "0008_chat_session"),
    ]

    operations = [
        # clear existing rows so we can safely swap session_key → session FK
        migrations.RunSQL("DELETE FROM agent_chatmessage;", migrations.RunSQL.noop),
        migrations.RemoveField(
            model_name="chatmessage",
            name="session_key",
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="session",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="agent.chatsession",
            ),
        ),
    ]
