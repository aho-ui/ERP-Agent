from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0014_chatmessage_steps'),
    ]

    operations = [
        migrations.AlterField(
            model_name='botinstance',
            name='platform',
            field=models.CharField(
                choices=[('discord', 'Discord'), ('telegram', 'Telegram'), ('whatsapp', 'WhatsApp')],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='agentaction',
            name='source',
            field=models.CharField(
                choices=[('web', 'Web'), ('discord', 'Discord'), ('telegram', 'Telegram'), ('whatsapp', 'WhatsApp'), ('system', 'System')],
                default='web',
                max_length=20,
            ),
        ),
    ]
