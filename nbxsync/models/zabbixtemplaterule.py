import logging
import re
from functools import lru_cache

from django.core.exceptions import ValidationError
from django.db import models
from netbox.models import NetBoxModel

logger = logging.getLogger(__name__)

__all__ = ('ZabbixTemplateRule',)

# Platform names are short. Keeping the cap low bounds the cost of a careless
# pattern without touching process-global signals (which break RQ job timeouts).
_MAX_MATCH_INPUT = 64
# Nested quantifiers like (a+)+ / (a*){2,} are the classic ReDoS shape.
_NESTED_QUANTIFIER = re.compile(r'(?<!\\)\([^)]*[+*][^)]*\)[+*{]')


@lru_cache(maxsize=256)
def _compiled_pattern(pattern):
    return re.compile(pattern, re.IGNORECASE)


class ZabbixTemplateRule(NetBoxModel):
    name = models.CharField(max_length=100, blank=False)
    description = models.CharField(max_length=200, blank=True)
    pattern = models.CharField(max_length=500, blank=False, help_text='Regex pattern matched against Platform name (case-insensitive substring search)')
    zabbixtemplate = models.ForeignKey(to='nbxsync.ZabbixTemplate', on_delete=models.PROTECT, related_name='zabbixtemplaterules')
    zabbixhostgroup = models.ForeignKey(to='nbxsync.ZabbixHostgroup', on_delete=models.SET_NULL, related_name='zabbixtemplaterules', blank=True, null=True, help_text='Optional hostgroup assigned when the rule matches')
    zabbixtag = models.ForeignKey(to='nbxsync.ZabbixTag', on_delete=models.SET_NULL, related_name='zabbixtemplaterules', blank=True, null=True, help_text='Optional tag assigned when the rule matches')
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=100, help_text='Lower value = higher priority')

    class Meta:
        verbose_name = 'Zabbix Template Rule'
        verbose_name_plural = 'Zabbix Template Rules'
        ordering = ('priority', 'name')

    def clean(self):
        super().clean()
        try:
            re.compile(self.pattern)
        except re.error as e:
            raise ValidationError({'pattern': f'Invalid regex: {e}'})

        if self.pattern and _NESTED_QUANTIFIER.search(self.pattern):
            raise ValidationError({'pattern': 'Pattern uses nested quantifiers that can cause catastrophic backtracking. Prefer a simpler expression (for example "Windows" or "Ubuntu|Debian").'})

        if self.zabbixhostgroup_id and self.zabbixtemplate_id:
            if self.zabbixhostgroup.zabbixserver_id != self.zabbixtemplate.zabbixserver_id:
                raise ValidationError({'zabbixhostgroup': 'Hostgroup must belong to the same Zabbix server as the template.'})
        # ZabbixTag is server-agnostic in nbxsync (no zabbixserver FK), so no
        # cross-server check applies for zabbixtag.

    def matches(self, platform_name):
        """Whether this rule applies to *platform_name*.

        Never raises: a rule that cannot be evaluated must not abort a host
        sync, and it must not match either — silently linking the wrong
        template is worse than linking none.
        """
        if not platform_name or not self.enabled:
            return False
        if len(platform_name) > _MAX_MATCH_INPUT:
            logger.warning('Rule "%s" not evaluated: platform name exceeds %s characters', self.name, _MAX_MATCH_INPUT)
            return False
        try:
            return bool(_compiled_pattern(self.pattern).search(platform_name))
        except re.error as err:
            # Patterns are validated on save, but a rule may predate that
            # validation or have been written directly to the database.
            logger.error('Rule "%s" has an invalid pattern "%s": %s', self.name, self.pattern, err)
            return False

    def __str__(self):
        return f'{self.name} ({self.pattern})'
