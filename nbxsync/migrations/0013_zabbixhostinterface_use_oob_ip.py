from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nbxsync', '0012_zabbixserver_skip_version_check'),
    ]

    operations = [
        migrations.AddField(
            model_name='zabbixhostinterface',
            name='use_oob_ip',
            field=models.BooleanField(
                default=False,
                verbose_name='Use OOB IP',
                help_text='When enabled and no static IP is set, the interface IP '
                          'will be resolved from the device\'s oob_ip field '
                          'instead of primary_ip4.',
            ),
        ),
    ]
