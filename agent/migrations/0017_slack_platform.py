from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0016_botmedia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='botinstance',
            name='platform',
            field=models.CharField(
                choices=[('discord', 'Discord'), ('telegram', 'Telegram'), ('whatsapp', 'WhatsApp'), ('slack', 'Slack')],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='agentaction',
            name='source',
            field=models.CharField(
                choices=[('web', 'Web'), ('discord', 'Discord'), ('telegram', 'Telegram'), ('whatsapp', 'WhatsApp'), ('slack', 'Slack'), ('system', 'System')],
                default='web',
                max_length=20,
            ),
        ),
    ]
