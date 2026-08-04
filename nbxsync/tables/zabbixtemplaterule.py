import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixTemplateRule

__all__ = ('ZabbixTemplateRuleTable', 'ZabbixTemplateRuleHostgroupViewTable')


class ZabbixTemplateRuleTable(NetBoxTable):
    name = tables.Column(linkify=True)
    zabbixtemplate = tables.Column(linkify=True)
    zabbixhostgroup = tables.Column(linkify=True)
    zabbixtag = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = ZabbixTemplateRule
        fields = (
            'pk',
            'name',
            'description',
            'pattern',
            'zabbixtemplate',
            'zabbixhostgroup',
            'zabbixtag',
            'enabled',
            'priority',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'name',
            'pattern',
            'zabbixtemplate',
            'zabbixhostgroup',
            'enabled',
            'priority',
        )


class ZabbixTemplateRuleHostgroupViewTable(NetBoxTable):
    """Compact rule table embedded on a ZabbixHostgroup detail page."""

    name = tables.Column(linkify=True)
    zabbixtemplate = tables.Column(linkify=True, verbose_name=_('Template'))
    pattern = tables.Column(verbose_name=_('Platform pattern'))
    require_tags = tables.Column(verbose_name=_('Require tags'))
    enabled = tables.BooleanColumn()
    priority = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = ZabbixTemplateRule
        fields = (
            'pk',
            'name',
            'pattern',
            'require_tags',
            'zabbixtemplate',
            'enabled',
            'priority',
        )
        default_columns = (
            'name',
            'pattern',
            'require_tags',
            'zabbixtemplate',
            'enabled',
            'priority',
        )
