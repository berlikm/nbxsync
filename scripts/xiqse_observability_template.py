#!/usr/bin/env python3
"""Render XIQ-SE / ExtremeControl Observability YAML from the JS contract."""

from __future__ import annotations

from pathlib import Path

from xiqse_observability import (
    NAC_TEMPLATE_DIR,
    NAC_YAML,
    SE_YAML,
    TEMPLATE_DIR,
    extract_engine_script,
    extract_license_engine_script,
    health_script,
    licenses_script,
    lld_script,
    pilot_script,
    yaml_literal,
)

GROUP_UUID = '36bff6c29af64692839d077febfc7079'
TPL = 'XIQ-SE Observability'
NAC = 'ExtremeControl Observability'

U = {
    'template': 'd66fadb95254489ebaaa0b5eb4e6763f',
    'vm_nbi': '3a97b114a68e416c97f5ab67825b74c3',
    'vm_bool': '16e31754297243d3a6340cdd9c7f4d96',
    'vm_trunc': '744bebe2d8254181b2e1cbda6db8cf12',
    'item_health': 'd8612bcd47b44c4cb60e679df06b67bd',
    'item_licenses': '774155de68b74b71b17bb24770360331',
    'item_pilot': '870e6b9527874183b9f0dc21946122e6',
    'item_avail': 'ff9d4a0c2bd243d3b50907d674c4c70d',
    'item_error': '546cd559cf1d419c9454382ddd7f9ba0',
    'item_version': '349eec0b35594c2aaa1bb6aeb18693a6',
    'item_uptime': 'ac95ffe740aa4381afc2b82fbf4bee2b',
    'item_heap_used': '085864f2324942d597d39328974a7569',
    'item_heap_max': '8fc39553db2244ab95c50def7bfc0bbe',
    'item_heap_pct': '2daf12be53ec4af1a1318e4d902faf99',
    'item_ram_free': 'c42cd56afa92461788dfa89f3eb23411',
    'item_ram_total': 'f9a83d5cc1b346c9892e96d3d588b17c',
    'item_threads': 'b083b3fd64b34c31b76e8f1aae7ff956',
    'item_engine_count': 'd78c94ad24b8400a90640848802268c8',
    'item_nac_used': '42078351037e4a66a77525e8918d919a',
    'item_nac_users': '7e7ca72601224d15a000bc81a5900db7',
    'item_nac_remain': '3fc85bb75873448a8f3b9e8db848f99f',
    'item_nac_pct': '6d891b6cf37f4276bc1beb250ade16ed',
    'item_nac_fetched': 'cc8ad599f96846f099bed5d33161f134',
    'item_nac_trunc': 'fe030b13c4db4f94a7281bbc1d0296d3',
    'item_nac_ok': '8c4e1f70a2b94d6e9f1a3c5d7e8b90a1',
    'item_nac_error': '9d5f2071b3ca4e7f0a2b4c6d8e9c01b2',
    'item_pilot_used': '9f94cfa9e6434a3288713564107fdbfb',
    'item_pilot_remain': '63a299d472f740c39b5d1bb7cced92fe',
    'item_pilot_ok': '03b45dacb57f42c2aacc1556bc8369e2',
    'item_nav_used': 'e739b887216f410da53afafe4294db58',
    'item_nav_remain': '679fe8d3980e4691a0c11a8be3d16ff0',
    'item_lic_pending': 'f152560225304bcd8adec843d76c532d',
    'item_lic_platformone': '6ad9ed0651a249578dbb63a07b0be9e7',
    'item_tcp8443': '1f2a9aae5987421e837ec9d3d21b4839',
    'item_unsupported': '35962793d7484596bee1d20ad9067757',
    'tr_avail': '97921d61a0b34d7286b85c77180bf3ce',
    'tr_nodata': '40dd971c943f4a01b7927b5f1afcf575',
    'tr_tcp': '810c1bc3b2a24f1b8fa47e29d2c21b1e',
    'tr_zero_eng': '9c7efefa14934d78a059dbfdebe249be',
    'tr_trunc': '9319f3e3d55b47b59a93b801857c846f',
    'tr_nac_fail': '0e6a3182c4db5f801b3c5d7e9f0d12c3',
    'tr_nac_cap': '12118b420e464f0ba5b63869fba1fb90',
    'tr_nac_warn': '5f355368b3ca4adc9ad31652151e2270',
    'tr_pilot_cap': '158689830fc5407b8522bedc7012ada8',
    'tr_pilot_low': '36805c7666e4437e9b083b4c9b58ee3f',
    'tr_nav_cap': 'b2c7a454475e4636b8199a4c08fb1340',
    'tr_nav_low': 'ce3614948ed94048983e6268e8651d27',
    'tr_reboot': 'd375ab5185f043d2bece3b826fe78e76',
    'tr_version': 'ca213b71fe584b7794cb053d766dcd61',
    'tr_unsup': '85d9c4f699e0491b9ad49a7bd5db11a3',
    'tr_pilot_fail': '3f6599c84332498485c73f96cd2353d7',
    'lld_engines': 'b122be820bea45eaacc37bad188fef00',
    'proto_licensed': '100cd1a56431429cb91cd8ff7a8d141b',
    'proto_connected': '8ea218cd93784f47be59584febef5c4f',
    'proto_enforce': 'a833fb6e1321428383e55ed5204f9663',
    'proto_radius': '6cf7d7dac82c4bc8840c491c5f1c5ce1',
    'proto_capacity': 'd255045f59544b94be7d383701432122',
    'proto_version': 'e9c853aaa79542bea5d4ff5f0d7d2300',
    'proto_used': '6221ca75b0dd4443ab804ae28a1c7327',
    'proto_age': 'e2df0122803749ab83062c589968491d',
    'tr_disc': 'da864acccba548148796be39ec378b3f',
    'tr_enf': 'a8410a22a38b45c6a326ac739ad65e1d',
    'tr_radius': '7e9aa7d8d6734243b446f4df80827c62',
    'tr_load': 'f200bad2977a4e058bb5eb4e496deea4',
    'tr_stale': '40f29028ce49433bacbfefc289c0bafe',
    'graph_used': 'd91bc047ac5342278b54654f3b384aa3',
    'proto_graph_used': 'b7babf7574ee45d08def304b49563f01',
    'proto_graph_age': '519df3a273054e78864b380573f02769',
    'dash_health': 'af01ea155ec841d68ff2c118f17f0040',
    'dash_engines': 'f22e74659b754873bc9958176cb81951',
    'vm_svc': 'c8f1a0b24d6e4c9f8a7b6c5d4e3f2a1b',
    'nac_template': '36b575ac588e4b7aa053ab032b3c6ac3',
    'nac_tcp': '12acf3f8703d49368e9c54f5d0898ef1',
    'nac_tr_tcp': 'd5155205a96c41d090036cf608fc9bb9',
    'nac_dash': '1c957a19146f46ef94da5522bdea4fc9',
    'nac_vm_svc': 'b9e0d1c24a3f4e5d8c7b6a5948372615',
}

TAGS_NBI = """      tags:
        - tag: component
          value: nbi
        - tag: scope
          value: health"""
TAGS_LIC = """      tags:
        - tag: component
          value: license
        - tag: scope
          value: health"""
TAGS_ENG = """              tags:
                - tag: component
                  value: engine
                - tag: engine
                  value: '{#ENGINE.NAME}'
                - tag: engine_ip
                  value: '{#ENGINE.IP}'"""


def _params(names: tuple[str, ...]) -> str:
    lines = ['      parameters:']
    for name in names:
        if name == 'fqdn':
            lines += ["        - name: fqdn", "          value: '{$XIQSE.API.FQDN}'"]
        elif name == 'port':
            lines += ["        - name: port", "          value: '{$XIQSE.API.PORT}'"]
        elif name == 'scheme':
            lines += ["        - name: scheme", "          value: '{$XIQSE.SCHEME}'"]
        elif name == 'client_id':
            lines += ["        - name: client_id", "          value: '{$XIQSE.API.CLIENT.ID}'"]
        elif name == 'client_secret':
            lines += ["        - name: client_secret", "          value: '{$XIQSE.API.CLIENT.SECRET}'"]
        elif name == 'max_results':
            lines += ["        - name: max_results", "          value: '{$XIQ.NAC.ES.MAXRESULTS}'"]
        elif name == 'page_size':
            lines += ["        - name: page_size", "          value: '{$XIQ.NAC.ES.PAGE}'"]
    return '\n'.join(lines)


AUTH_PARAMS = ('fqdn', 'port', 'scheme', 'client_id', 'client_secret')
LICENSE_PARAMS = AUTH_PARAMS + ('max_results', 'page_size')


def bump(text: str, spaces: int = 4) -> str:
    pad = ' ' * spaces
    return '\n'.join(pad + line if line else line for line in text.split('\n'))


def _script_item(uuid: str, name: str, key: str, delay: str, timeout: str, script: str, params: tuple[str, ...], extra: str = '') -> str:
    return f"""    - uuid: {uuid}
      name: {name}
      type: SCRIPT
      key: {key}
      delay: {delay}
      history: 7d
      trends: '0'
      value_type: TEXT
      params: |
{yaml_literal(script, 8)}
      timeout: '{timeout}'
{_params(params)}
{extra}{TAGS_NBI}"""


def _dep(uuid: str, name: str, key: str, master: str, jpath: str, value_type: str, units: str = '', extra: str = '', tags: str = TAGS_NBI) -> str:
    units_l = ("\n      units: '" + units + "'") if units else ''
    hist = '7d' if value_type in {'FLOAT', 'UNSIGNED'} else '7d'
    trends = "      trends: 365d\n" if value_type in {'FLOAT', 'UNSIGNED'} else "      trends: '0'\n"
    return f"""    - uuid: {uuid}
      name: {name}
      type: DEPENDENT
      key: {key}
      delay: '0'
      history: {hist}
{trends}      value_type: {value_type}{units_l}
      preprocessing:
        - type: JSONPATH
          parameters:
            - '{jpath}'
      master_item:
        key: {master}
{extra}{tags}"""


def _calc(uuid: str, name: str, key: str, params: str, units: str = '', extra: str = '', tags: str = TAGS_LIC) -> str:
    units_l = ("\n      units: '" + units + "'") if units else ''
    return f"""    - uuid: {uuid}
      name: {name}
      type: CALCULATED
      key: {key}
      delay: 1m
      history: 7d
      trends: 365d
      value_type: FLOAT{units_l}
      params: '{params}'
{extra}{tags}"""


def _trigger(uuid: str, expression: str, name: str, priority: str, description: str, extra: str = '') -> str:
    return f"""        - uuid: {uuid}
          expression: '{expression}'
          name: '{name}'
          event_name: '{name}'
          priority: {priority}
          description: |
            {description}
{extra}          tags:
            - tag: scope
              value: availability"""


def render_se() -> str:
    health = _script_item(
        U['item_health'],
        'XIQ-SE NBI health snapshot',
        'xiqse.nbi.health',
        '2m',
        '{$XIQSE.DATA.TIMEOUT}',
        health_script(),
        AUTH_PARAMS,
        extra="      description: |\n        OAuth + serverInfo + engines. Query only. New HttpRequest per call.\n",
    )
    licenses = _script_item(
        U['item_licenses'],
        'XIQ-SE NAC 24h unique snapshot',
        'xiqse.nbi.licenses',
        '15m',
        '{$XIQSE.LICENSE.TIMEOUT}',
        licenses_script(),
        LICENSE_PARAMS,
        extra="      description: |\n        Pages endSystems and counts unique MACs with lastAuthEventTime in 24h.\n",
    )
    licenses = licenses.replace(TAGS_NBI, TAGS_LIC)
    pilot = _script_item(
        U['item_pilot'],
        'XIQ-SE device license snapshot',
        'xiqse.nbi.pilot',
        '15m',
        '{$XIQSE.LICENSE.TIMEOUT}',
        pilot_script(),
        AUTH_PARAMS,
        extra="      description: |\n        Counts network.devices xiqLicenseState: Pilot, Navigator, pending, Platform ONE.\n",
    )
    pilot = pilot.replace(TAGS_NBI, TAGS_LIC)

    avail_tr = _trigger(
        U['tr_avail'],
        f'min(/{TPL}/xiqse.nbi.available,5m)=0',
        'XIQ-SE: NBI unexpected response',
        'AVERAGE',
        'OAuth or GraphQL failed while the host is still polled. RADIUS on engines may still work.',
        extra=f"""          dependencies:
            - name: 'XIQ-SE: HTTPS 8443 down'
              expression: 'max(/{TPL}/net.tcp.service[tcp,{{$XIQSE.API.FQDN}},{{$XIQSE.API.PORT}}],#3)=0'
""",
    )
    nodata_tr = _trigger(
        U['tr_nodata'],
        f'nodata(/{TPL}/xiqse.nbi.health,15m)=1',
        'XIQ-SE: no NBI data for 15m',
        'AVERAGE',
        'Health SCRIPT produced no values. Token, proxy, or TLS.',
    )
    trunc_tr = _trigger(
        U['tr_trunc'],
        f'last(/{TPL}/xiqse.nac.truncated)=1',
        'XIQ-SE: 24h end-system census truncated',
        'AVERAGE',
        'Fetched count hit {$XIQ.NAC.ES.MAXRESULTS}. The NAC license graph under-counts.',
    )
    nac_fail = _trigger(
        U['tr_nac_fail'],
        f'last(/{TPL}/xiqse.nac.ok)=0 and last(/{TPL}/xiqse.nbi.available)=1',
        'XIQ-SE: NAC census failed',
        'AVERAGE',
        'NBI is up but the endSystems 24h unique query failed. NAC used/remaining stay empty until it succeeds.',
    )
    nac_cap = _trigger(
        U['tr_nac_cap'],
        f'{{$XIQ.NAC.TOTAL}}>0 and last(/{TPL}/xiqse.nac.used24h)>={{$XIQ.NAC.TOTAL}}',
        'XIQ-SE: NAC license seats exhausted',
        'AVERAGE',
        'Unique MACs authenticated in 24h reached {$XIQ.NAC.TOTAL} (XIQ-NAC-S).',
    )
    nac_warn = _trigger(
        U['tr_nac_warn'],
        f'{{$XIQ.NAC.TOTAL}}>0 and last(/{TPL}/xiqse.nac.used24h)*100>={{$XIQ.NAC.TOTAL}}*{{$XIQ.NAC.USED.WARN}}',
        'XIQ-SE: NAC license seats high',
        'WARNING',
        '24h unique MACs at or above {$XIQ.NAC.USED.WARN}% of {$XIQ.NAC.TOTAL}.',
        extra=f"""          dependencies:
            - name: 'XIQ-SE: NAC license seats exhausted'
              expression: '{{$XIQ.NAC.TOTAL}}>0 and last(/{TPL}/xiqse.nac.used24h)>={{$XIQ.NAC.TOTAL}}'
""",
    )
    pilot_fail = _trigger(
        U['tr_pilot_fail'],
        f'last(/{TPL}/xiqse.pilot.ok)=0 and last(/{TPL}/xiqse.nbi.available)=1',
        'XIQ-SE: Pilot census failed',
        'AVERAGE',
        'NBI is up but the devices xiqLicenseState query failed. Pilot and Navigator remaining are unknown.',
    )
    pilot_cap = _trigger(
        U['tr_pilot_cap'],
        f'{{$XIQ.PILOT.TOTAL}}>0 and last(/{TPL}/xiqse.pilot.ok)=1 and last(/{TPL}/xiqse.pilot.used)>={{$XIQ.PILOT.TOTAL}}',
        'XIQ-SE: Pilot licenses exhausted',
        'WARNING',
        'Cannot onboard another switch or Control engine.',
    )
    pilot_low = _trigger(
        U['tr_pilot_low'],
        f'{{$XIQ.PILOT.TOTAL}}>0 and last(/{TPL}/xiqse.pilot.ok)=1 and last(/{TPL}/xiqse.pilot.remaining)<={{$XIQ.PILOT.REMAIN.WARN}}',
        'XIQ-SE: few Pilot licenses remaining',
        'WARNING',
        'Pilot remaining at or below {$XIQ.PILOT.REMAIN.WARN}.',
        extra=f"""          dependencies:
            - name: 'XIQ-SE: Pilot licenses exhausted'
              expression: '{{$XIQ.PILOT.TOTAL}}>0 and last(/{TPL}/xiqse.pilot.ok)=1 and last(/{TPL}/xiqse.pilot.used)>={{$XIQ.PILOT.TOTAL}}'
""",
    )
    nav_cap = _trigger(
        U['tr_nav_cap'],
        f'{{$XIQ.NAV.TOTAL}}>0 and last(/{TPL}/xiqse.pilot.ok)=1 and last(/{TPL}/xiqse.nav.used)>={{$XIQ.NAV.TOTAL}}',
        'XIQ-SE: Navigator licenses exhausted',
        'WARNING',
        'Cannot onboard another Navigator-tier device.',
    )
    nav_low = _trigger(
        U['tr_nav_low'],
        f'{{$XIQ.NAV.TOTAL}}>0 and last(/{TPL}/xiqse.pilot.ok)=1 and last(/{TPL}/xiqse.nav.remaining)<={{$XIQ.NAV.REMAIN.WARN}}',
        'XIQ-SE: few Navigator licenses remaining',
        'WARNING',
        'Navigator remaining at or below {$XIQ.NAV.REMAIN.WARN}.',
        extra=f"""          dependencies:
            - name: 'XIQ-SE: Navigator licenses exhausted'
              expression: '{{$XIQ.NAV.TOTAL}}>0 and last(/{TPL}/xiqse.pilot.ok)=1 and last(/{TPL}/xiqse.nav.used)>={{$XIQ.NAV.TOTAL}}'
""",
    )
    reboot = _trigger(
        U['tr_reboot'],
        f'last(/{TPL}/xiqse.nbi.uptime)>0 and last(/{TPL}/xiqse.nbi.uptime)<10m',
        'XIQ-SE: unplanned reboot',
        'WARNING',
        'JVM upTime dropped below 10 minutes.',
    )
    version = _trigger(
        U['tr_version'],
        f'change(/{TPL}/xiqse.nbi.version)<>0 and length(last(/{TPL}/xiqse.nbi.version))>0',
        'XIQ-SE: version has changed',
        'INFO',
        'Site Engine version string changed.',
        extra="          manual_close: 'YES'\n",
    )
    zero = _trigger(
        U['tr_zero_eng'],
        f'last(/{TPL}/xiqse.nbi.available)=1 and last(/{TPL}/xiqse.engine.count)=0',
        'XIQ-SE: no Control engines discovered',
        'AVERAGE',
        'NBI is up but engines is empty. Access Control NBI right or filter.',
    )
    unsup = _trigger(
        U['tr_unsup'],
        f'last(/{TPL}/zabbix[host,,items_unsupported])>0',
        'XIQ-SE: unsupported items present',
        'AVERAGE',
        'Schema field missing or SCRIPT error.',
    )

    tcp_item = f"""    - uuid: {U['item_tcp8443']}
      name: XIQ-SE HTTPS 8443
      type: SIMPLE
      key: 'net.tcp.service[tcp,{{$XIQSE.API.FQDN}},{{$XIQSE.API.PORT}}]'
      delay: 1m
      history: 7d
      trends: 365d
      value_type: UNSIGNED
      valuemap:
        name: 'Service state'
      tags:
        - tag: component
          value: nbi
        - tag: scope
          value: health
      triggers:
        - uuid: {U['tr_tcp']}
          expression: 'max(/{TPL}/net.tcp.service[tcp,{{$XIQSE.API.FQDN}},{{$XIQSE.API.PORT}}],#3)=0'
          name: 'XIQ-SE: HTTPS 8443 down'
          event_name: 'XIQ-SE: HTTPS 8443 down'
          priority: AVERAGE
          description: |
            NBI/GUI port is closed. RADIUS on engines may still work.
          tags:
            - tag: scope
              value: availability"""


    dash = _se_dashboards()
    macros = _se_macros()

    avail_item = _dep(U['item_avail'], 'XIQ-SE NBI available', 'xiqse.nbi.available', 'xiqse.nbi.health', '$.ok', 'UNSIGNED', extra=f'      valuemap:\n        name: XIQ-SE NBI\n      triggers:\n{avail_tr}\n{nodata_tr}\n')
    error_item = _dep(U['item_error'], 'XIQ-SE NBI last error', 'xiqse.nbi.error', 'xiqse.nbi.health', '$.error', 'TEXT')
    version_item = _dep(U['item_version'], 'XIQ-SE version', 'xiqse.nbi.version', 'xiqse.nbi.health', '$.version', 'TEXT', extra=f'      triggers:\n{version}\n')
    uptime_item = _dep(U['item_uptime'], 'XIQ-SE uptime', 'xiqse.nbi.uptime', 'xiqse.nbi.health', '$.upTime', 'UNSIGNED', units='uptime', extra=f'      triggers:\n{reboot}\n')
    heap_used = _dep(U['item_heap_used'], 'XIQ-SE heap used', 'xiqse.nbi.heap.used', 'xiqse.nbi.health', '$.heapMemoryUsed', 'FLOAT', units='B')
    heap_max = _dep(U['item_heap_max'], 'XIQ-SE heap max', 'xiqse.nbi.heap.max', 'xiqse.nbi.health', '$.heapMemoryMax', 'FLOAT', units='B')
    ram_free = _dep(U['item_ram_free'], 'XIQ-SE free physical memory', 'xiqse.nbi.ram.free', 'xiqse.nbi.health', '$.freePhysicalMemory', 'FLOAT', units='B')
    ram_total = _dep(U['item_ram_total'], 'XIQ-SE total physical memory', 'xiqse.nbi.ram.total', 'xiqse.nbi.health', '$.totalPhysicalMemory', 'FLOAT', units='B')
    threads = _dep(U['item_threads'], 'XIQ-SE threads', 'xiqse.nbi.threads', 'xiqse.nbi.health', '$.threadCount', 'FLOAT')
    eng_count = _dep(
        U['item_engine_count'],
        'XIQ-SE Control engine count',
        'xiqse.engine.count',
        'xiqse.nbi.health',
        '$.engineCount',
        'UNSIGNED',
        extra=f'      triggers:\n{zero}\n',
    )
    nac_used = _dep(U['item_nac_used'], 'NAC license used (24h unique MACs)', 'xiqse.nac.used24h', 'xiqse.nbi.licenses', '$.nacUsed24h', 'UNSIGNED', extra=f'      triggers:\n{nac_cap}\n{nac_warn}\n', tags=TAGS_LIC)
    nac_users = _dep(U['item_nac_users'], 'NAC unique usernames (24h)', 'xiqse.nac.users24h', 'xiqse.nbi.licenses', '$.users24h', 'UNSIGNED', tags=TAGS_LIC)
    nac_fetched = _dep(U['item_nac_fetched'], 'NAC end-systems fetched', 'xiqse.nac.fetched', 'xiqse.nbi.licenses', '$.fetched', 'UNSIGNED', tags=TAGS_LIC)
    nac_trunc = _dep(
        U['item_nac_trunc'],
        'NAC 24h census truncated',
        'xiqse.nac.truncated',
        'xiqse.nbi.licenses',
        '$.truncated',
        'UNSIGNED',
        extra=f'      valuemap:\n        name: XIQ-SE truncated\n      triggers:\n{trunc_tr}\n',
        tags=TAGS_LIC,
    )
    nac_ok = _dep(
        U['item_nac_ok'],
        'NAC census ok',
        'xiqse.nac.ok',
        'xiqse.nbi.licenses',
        '$.ok',
        'UNSIGNED',
        extra=f'      valuemap:\n        name: XIQ-SE NBI\n      triggers:\n{nac_fail}\n',
        tags=TAGS_LIC,
    )
    nac_err = _dep(U['item_nac_error'], 'NAC census last error', 'xiqse.nac.error', 'xiqse.nbi.licenses', '$.error', 'TEXT', tags=TAGS_LIC)
    pilot_used = _dep(U['item_pilot_used'], 'Pilot licenses used', 'xiqse.pilot.used', 'xiqse.nbi.pilot', '$.pilotUsed', 'UNSIGNED', extra=f'      triggers:\n{pilot_cap}\n', tags=TAGS_LIC)
    nav_used = _dep(U['item_nav_used'], 'Navigator licenses used', 'xiqse.nav.used', 'xiqse.nbi.pilot', '$.navigatorUsed', 'UNSIGNED', extra=f'      triggers:\n{nav_cap}\n', tags=TAGS_LIC)
    lic_pending = _dep(U['item_lic_pending'], 'Device licenses pending', 'xiqse.lic.pending', 'xiqse.nbi.pilot', '$.pending', 'UNSIGNED', tags=TAGS_LIC)
    lic_pone = _dep(U['item_lic_platformone'], 'Platform ONE / Advanced / Standard used', 'xiqse.lic.platformone', 'xiqse.nbi.pilot', '$.platformOne', 'UNSIGNED', tags=TAGS_LIC)
    pilot_ok = _dep(U['item_pilot_ok'], 'Pilot census ok', 'xiqse.pilot.ok', 'xiqse.nbi.pilot', '$.ok', 'UNSIGNED', extra=f'      valuemap:\n        name: XIQ-SE NBI\n      triggers:\n{pilot_fail}\n', tags=TAGS_LIC)
    heap_pct = _calc(U['item_heap_pct'], 'XIQ-SE heap used %', 'xiqse.nbi.heap.pct', 'last(//xiqse.nbi.heap.used)/(last(//xiqse.nbi.heap.max)+(last(//xiqse.nbi.heap.max)=0))*100', '%', tags=TAGS_NBI)
    nac_remain = _calc(
        U['item_nac_remain'],
        'NAC license remaining',
        'xiqse.nac.remaining',
        '({$XIQ.NAC.TOTAL}-last(//xiqse.nac.used24h))*({$XIQ.NAC.TOTAL}>0)',
    )
    nac_pct = _calc(U['item_nac_pct'], 'NAC license used %', 'xiqse.nac.used.pct', 'last(//xiqse.nac.used24h)/({$XIQ.NAC.TOTAL}+({$XIQ.NAC.TOTAL}=0))*100*({$XIQ.NAC.TOTAL}>0)', '%')
    pilot_remain = _calc(
        U['item_pilot_remain'],
        'Pilot licenses remaining',
        'xiqse.pilot.remaining',
        '({$XIQ.PILOT.TOTAL}-last(//xiqse.pilot.used))*({$XIQ.PILOT.TOTAL}>0)',
        extra=f'      triggers:\n{pilot_low}\n',
    )
    nav_remain = _calc(
        U['item_nav_remain'],
        'Navigator licenses remaining',
        'xiqse.nav.remaining',
        '({$XIQ.NAV.TOTAL}-last(//xiqse.nav.used))*({$XIQ.NAV.TOTAL}>0)',
        extra=f'      triggers:\n{nav_low}\n',
    )
    unsup_item = f"""    - uuid: {U['item_unsupported']}
      name: Unsupported items
      type: INTERNAL
      key: 'zabbix[host,,items_unsupported]'
      delay: 15m
      history: 7d
      trends: 365d
      value_type: UNSIGNED
      tags:
        - tag: component
          value: census
      triggers:
{unsup}"""

    return f"""zabbix_export:
  version: '7.0'
  template_groups:
    - uuid: {GROUP_UUID}
      name: Templates/Network devices
  templates:
    - uuid: {U['template']}
      template: {TPL}
      name: {TPL}
      description: |
        ExtremeCloud IQ Site Engine companion. HTTPS GraphQL (OAuth client
        credentials) from the proxy. Does not nest ICMP Ping — OS/ICMP stay on
        the VM / Agent Monitoring path. Do not GraphQL Control engines. Do not
        install an agent on the OVA for this pack.

        Operator page: zabbix/07-extreme-control.md.
        Refresh with configure_nbxsync_network.py --apply-xiqse.
      groups:
        - name: Templates/Network devices
{macros}
      items:
{bump(health)}
{bump(licenses)}
{bump(pilot)}
{bump(avail_item)}
{bump(error_item)}
{bump(version_item)}
{bump(uptime_item)}
{bump(heap_used)}
{bump(heap_max)}
{bump(heap_pct)}
{bump(ram_free)}
{bump(ram_total)}
{bump(threads)}
{bump(eng_count)}
{bump(nac_used)}
{bump(nac_users)}
{bump(nac_remain)}
{bump(nac_pct)}
{bump(nac_fetched)}
{bump(nac_trunc)}
{bump(nac_ok)}
{bump(nac_err)}
{bump(pilot_used)}
{bump(pilot_remain)}
{bump(nav_used)}
{bump(nav_remain)}
{bump(lic_pending)}
{bump(lic_pone)}
{bump(pilot_ok)}
{bump(tcp_item)}
{bump(unsup_item)}
{_prototypes()}
      tags:
        - tag: class
          value: network
        - tag: target
          value: xiq-se
{dash}
      valuemaps:
        - uuid: {U['vm_nbi']}
          name: XIQ-SE NBI
          mappings:
            - value: '0'
              newvalue: Down
            - value: '1'
              newvalue: Up
        - uuid: {U['vm_bool']}
          name: XIQ-SE tri-state
          mappings:
            - value: '0'
              newvalue: No
            - value: '1'
              newvalue: Yes
            - value: '2'
              newvalue: Unknown
        - uuid: {U['vm_trunc']}
          name: XIQ-SE truncated
          mappings:
            - value: '0'
              newvalue: Complete
            - value: '1'
              newvalue: Truncated
        - uuid: {U['vm_svc']}
          name: 'Service state'
          mappings:
            - value: '0'
              newvalue: Down
            - value: '1'
              newvalue: Up
"""


def _se_macros() -> str:
    rows = [
        ('{$XIQSE.API.FQDN}', '', 'Site Engine FQDN or IP. Platform Jinja on primary_ip4.'),
        ('{$XIQSE.API.PORT}', '8443', 'NBI HTTPS port.'),
        ('{$XIQSE.SCHEME}', 'https', 'http only for a lab break-glass.'),
        ('{$XIQSE.API.CLIENT.ID}', '', 'Client API Access id. Prefer a secret CG over YAML.'),
        ('{$XIQSE.API.CLIENT.SECRET}', '', 'Client API Access secret.', 'SECRET_TEXT'),
        ('{$XIQSE.DATA.TIMEOUT}', '30s', 'Health SCRIPT timeout.'),
        ('{$XIQSE.LICENSE.TIMEOUT}', '60s', 'End-system / device-license SCRIPT timeout.'),
        ('{$XIQ.NAC.TOTAL}', '0', 'Purchased XIQ-NAC-S end-systems. 0 = graph used only.'),
        ('{$XIQ.NAC.USED.WARN}', '90', 'Warning percent of {$XIQ.NAC.TOTAL}.'),
        ('{$XIQ.NAC.ES.MAXRESULTS}', '20000', 'Stop paging at this many end-system rows.'),
        ('{$XIQ.NAC.ES.PAGE}', '500', 'endSystems page size.'),
        ('{$XIQ.NAC.FRESH}', '86400', 'Auth-event stale after this many seconds. Per engine: {$XIQ.NAC.FRESH:"<engine-ip>"}.'),
        ('{$XIQ.NAC.FRESH.CONTROL}', '1', 'Ticket stale auth events. No clock window — engines are in different time zones.'),
        ('{$XIQ.PILOT.TOTAL}', '0', 'Purchased Pilot seats. 0 = graph used only.'),
        ('{$XIQ.PILOT.REMAIN.WARN}', '2', 'Warning when remaining Pilot seats at or below this.'),
        ('{$XIQ.NAV.TOTAL}', '0', 'Purchased Navigator seats. 0 = graph used only.'),
        ('{$XIQ.NAV.REMAIN.WARN}', '2', 'Warning when remaining Navigator seats at or below this.'),
        ('{$XIQ.ENGINE.CONNECTED.CONTROL}', '1', 'Ticket engines with connected=0. Unknown (2) is silent.'),
        ('{$XIQ.ENGINE.ENFORCE.CONTROL}', '1', 'Ticket needsEnforce=1.'),
        ('{$XIQ.ENGINE.RADIUSD.CONTROL}', '1', 'Page FreeRADIUS disabled on an engine.'),
    ]
    lines = ['      macros:']
    for row in rows:
        macro, value, desc = row[0], row[1], row[2]
        typ = row[3] if len(row) > 3 else None
        lines.append(f"        - macro: '{macro}'")
        if typ:
            lines.append(f'          type: {typ}')
        lines.append(f"          value: '{value}'")
        lines.append(f"          description: '{desc}'")
    return '\n'.join(lines)


def _proto_js(field: str, missing: str) -> str:
    return yaml_literal(extract_engine_script(field, missing), 22)


def _proto_lic_js(field: str, missing: str) -> str:
    return yaml_literal(extract_license_engine_script(field, missing), 22)


def _prototypes() -> str:
    def proto(uuid: str, name: str, key: str, master: str, script: str, value_type: str, units: str, valuemap: str, triggers: str) -> str:
        units_l = ("\n              units: '" + units + "'") if units else ''
        vm = f"\n              valuemap:\n                name: '{valuemap}'" if valuemap else ''
        trends = "              trends: 365d\n" if value_type in {'FLOAT', 'UNSIGNED'} else "              trends: '0'\n"
        trig = f'\n              trigger_prototypes:\n{bump(triggers, 8)}' if triggers else ''
        return f"""            - uuid: {uuid}
              name: '{name}'
              type: DEPENDENT
              key: '{key}'
              delay: '0'
              history: 7d
{trends}              value_type: {value_type}{units_l}{vm}
              preprocessing:
                - type: JAVASCRIPT
                  parameters:
                    - |
{script}
              master_item:
                key: {master}
{TAGS_ENG}{trig}"""

    disc = _trigger(
        U['tr_disc'],
        f'{{$XIQ.ENGINE.CONNECTED.CONTROL}}=1 and last(/{TPL}/xiqse.nbi.available)=1 and last(/{TPL}/xiqse.engine.connected[{{#ENGINE.IP}}])=0',
        'XIQ-SE engine {#ENGINE.NAME}: disconnected from Site Engine',
        'AVERAGE',
        'SE lists the engine as connected=0. Auth may still work locally.',
    )
    enf = _trigger(
        U['tr_enf'],
        f'{{$XIQ.ENGINE.ENFORCE.CONTROL}}=1 and last(/{TPL}/xiqse.engine.needs_enforce[{{#ENGINE.IP}}])=1',
        'XIQ-SE engine {#ENGINE.NAME}: needs enforce',
        'AVERAGE',
        'Config never pushed to this engine.',
    )
    radius = _trigger(
        U['tr_radius'],
        f'{{$XIQ.ENGINE.RADIUSD.CONTROL}}=1 and last(/{TPL}/xiqse.engine.freeradius[{{#ENGINE.IP}}])=0',
        'XIQ-SE engine {#ENGINE.NAME}: FreeRADIUS disabled',
        'HIGH',
        'NBI reports freeRadiusEnabled=false. Users fail 802.1X on this engine.',
    )
    load = _trigger(
        U['tr_load'],
        f'last(/{TPL}/xiqse.engine.capacity[{{#ENGINE.IP}}])>0 and last(/{TPL}/xiqse.engine.used24h[{{#ENGINE.IP}}])>=last(/{TPL}/xiqse.engine.capacity[{{#ENGINE.IP}}])',
        'XIQ-SE engine {#ENGINE.NAME}: 24h unique MACs at hardware capacity',
        'WARNING',
        'Per-engine hardware load (Current Capacity), not the global NAC license.',
    )
    stale = _trigger(
        U['tr_stale'],
        f'{{$XIQ.NAC.FRESH.CONTROL}}=1 and last(/{TPL}/xiqse.nbi.available)=1 and last(/{TPL}/xiqse.engine.auth.age[{{#ENGINE.IP}}])>={{$XIQ.NAC.FRESH:"{{#ENGINE.IP}}"}}',
        'XIQ-SE engine {#ENGINE.NAME}: not forwarding auth logs',
        'AVERAGE',
        'NAC to SE log-forward: no lastAuthEventTime on Site Engine within {$XIQ.NAC.FRESH} (elapsed seconds, any time zone). Override per engine with {$XIQ.NAC.FRESH:"<engine-ip>"}. RADIUS on the engine may still work. Not syslog to a SIEM.',
    )

    graph = f"""          graph_prototypes:
            - uuid: {U['proto_graph_used']}
              name: 'Engine {{#ENGINE.NAME}}: 24h unique MACs'
              graph_items:
                - color: 2774A4
                  item:
                    host: {TPL}
                    key: 'xiqse.engine.used24h[{{#ENGINE.IP}}]'
            - uuid: {U['proto_graph_age']}
              name: 'Engine {{#ENGINE.NAME}}: last auth age'
              graph_items:
                - color: E68931
                  item:
                    host: {TPL}
                    key: 'xiqse.engine.auth.age[{{#ENGINE.IP}}]'"""

    return f"""      discovery_rules:
        - uuid: {U['lld_engines']}
          name: Control engine discovery
          type: DEPENDENT
          key: xiqse.engine.discovery
          delay: '0'
          lifetime: 7d
          lifetime_type: DELETE_AFTER
          enabled_lifetime: '0'
          enabled_lifetime_type: DISABLE_IMMEDIATELY
          description: |
            Engines from the health snapshot. Never LLD end-system MACs.
          preprocessing:
            - type: JAVASCRIPT
              parameters:
                - |
{yaml_literal(lld_script(), 18)}
          master_item:
            key: xiqse.nbi.health
          item_prototypes:
{proto(U['proto_licensed'], 'Engine {#ENGINE.NAME}: Licensed', 'xiqse.engine.licensed[{#ENGINE.IP}]', 'xiqse.nbi.health', _proto_js('licensed', '2'), 'UNSIGNED', '', 'XIQ-SE tri-state', '')}
{proto(U['proto_connected'], 'Engine {#ENGINE.NAME}: Connected', 'xiqse.engine.connected[{#ENGINE.IP}]', 'xiqse.nbi.health', _proto_js('connected', '2'), 'UNSIGNED', '', 'XIQ-SE tri-state', disc)}
{proto(U['proto_enforce'], 'Engine {#ENGINE.NAME}: Needs enforce', 'xiqse.engine.needs_enforce[{#ENGINE.IP}]', 'xiqse.nbi.health', _proto_js('needsEnforce', '2'), 'UNSIGNED', '', 'XIQ-SE tri-state', enf)}
{proto(U['proto_radius'], 'Engine {#ENGINE.NAME}: FreeRADIUS', 'xiqse.engine.freeradius[{#ENGINE.IP}]', 'xiqse.nbi.health', _proto_js('freeRadiusEnabled', '2'), 'UNSIGNED', '', 'XIQ-SE tri-state', radius)}
{proto(U['proto_capacity'], 'Engine {#ENGINE.NAME}: Hardware capacity', 'xiqse.engine.capacity[{#ENGINE.IP}]', 'xiqse.nbi.health', _proto_js('capacity', '0'), 'UNSIGNED', '', '', '')}
{proto(U['proto_version'], 'Engine {#ENGINE.NAME}: Version', 'xiqse.engine.version[{#ENGINE.IP}]', 'xiqse.nbi.health', _proto_js('version', "''"), 'TEXT', '', '', '')}
{proto(U['proto_used'], 'Engine {#ENGINE.NAME}: 24h unique MACs', 'xiqse.engine.used24h[{#ENGINE.IP}]', 'xiqse.nbi.licenses', _proto_lic_js('used24h', '0'), 'UNSIGNED', '', '', load)}
{proto(U['proto_age'], 'Engine {#ENGINE.NAME}: last auth age', 'xiqse.engine.auth.age[{#ENGINE.IP}]', 'xiqse.nbi.licenses', _proto_lic_js('lastAuthAge', '-1'), 'FLOAT', 's', '', stale)}
{graph}"""


def _item_widget(name: str, x: str, key: str, ref: str) -> str:
    x_l = f"\n                  x: '{x}'" if x and x != '0' else ''
    return f"""                - type: item
                  name: {name}{x_l}
                  width: '18'
                  height: '4'
                  fields:
                    - type: ITEM
                      name: itemid.0
                      value:
                        host: {TPL}
                        key: {key}
                    - type: INTEGER
                      name: show.0
                      value: '2'
                    - type: INTEGER
                      name: value_bold
                      value: '1'
                    - type: INTEGER
                      name: value_size
                      value: '28'
                    - type: STRING
                      name: reference
                      value: {ref}"""


def _se_dashboards() -> str:
    honeycomb = """                - type: honeycomb
                  name: Connected
                  y: '4'
                  width: '72'
                  height: '5'
                  fields:
                    - type: STRING
                      name: items.0
                      value: 'Engine *: Connected'
                    - type: STRING
                      name: primary_label
                      value: '{{ITEM.NAME}.regsub("^Engine (.*): Connected$","\\1")}'
                    - type: INTEGER
                      name: interpolation
                      value: '0'
                    - type: INTEGER
                      name: primary_label_bold
                      value: '1'
                    - type: INTEGER
                      name: primary_label_size_type
                      value: '1'
                    - type: INTEGER
                      name: primary_label_size
                      value: '20'
                    - type: INTEGER
                      name: show.0
                      value: '1'
                    - type: STRING
                      name: reference
                      value: XECON
                    - type: STRING
                      name: thresholds.0.color
                      value: 'FF465C'
                    - type: STRING
                      name: thresholds.0.threshold
                      value: '0'
                    - type: STRING
                      name: thresholds.1.color
                      value: '0EC9AC'
                    - type: STRING
                      name: thresholds.1.threshold
                      value: '1'
                    - type: STRING
                      name: thresholds.2.color
                      value: '878787'
                    - type: STRING
                      name: thresholds.2.threshold
                      value: '2'"""
    radius_h = honeycomb.replace('Connected', 'FreeRADIUS').replace('XECON', 'XERAD').replace(
        'Engine *: Connected', 'Engine *: FreeRADIUS'
    ).replace('^Engine (.*): Connected$', '^Engine (.*): FreeRADIUS$')
    radius_h = radius_h.replace("y: '4'", "y: '9'")
    return f"""      dashboards:
        - uuid: {U['dash_health']}
          name: Health
          pages:
            - name: Overview
              widgets:
{_item_widget('NBI', '0', 'xiqse.nbi.available', 'XNBI')}
{_item_widget('NAC 24h MACs', '18', 'xiqse.nac.used24h', 'XNAC')}
{_item_widget('Pilot used', '36', 'xiqse.pilot.used', 'XPUO')}
{_item_widget('Navigator used', '54', 'xiqse.nav.used', 'XNUO')}
                - type: problems
                  name: Problems
                  y: '4'
                  width: '72'
                  height: '4'
                  fields:
                    - type: STRING
                      name: reference
                      value: XPROB
                    - type: INTEGER
                      name: show
                      value: '3'
                - type: svggraph
                  name: NAC license (24h unique MACs)
                  y: '8'
                  width: '36'
                  height: '6'
                  fields:
                    - type: STRING
                      name: ds.0.color.0
                      value: 2774A4
                    - type: INTEGER
                      name: ds.0.dataset_type
                      value: '0'
                    - type: ITEM
                      name: ds.0.itemids.0
                      value:
                        host: {TPL}
                        key: xiqse.nac.used24h
                    - type: STRING
                      name: reference
                      value: XNACG
                    - type: INTEGER
                      name: show_problems
                      value: '1'
                    - type: INTEGER
                      name: legend
                      value: '1'
                - type: svggraph
                  name: Heap
                  x: '36'
                  y: '8'
                  width: '36'
                  height: '6'
                  fields:
                    - type: STRING
                      name: ds.0.color.0
                      value: 199C0D
                    - type: INTEGER
                      name: ds.0.dataset_type
                      value: '0'
                    - type: ITEM
                      name: ds.0.itemids.0
                      value:
                        host: {TPL}
                        key: xiqse.nbi.heap.pct
                    - type: STRING
                      name: lefty_max
                      value: '100'
                    - type: STRING
                      name: lefty_min
                      value: '0'
                    - type: STRING
                      name: reference
                      value: XHEAP
                    - type: INTEGER
                      name: legend
                      value: '0'
            - name: Licenses
              widgets:
{_item_widget('NAC remaining', '0', 'xiqse.nac.remaining', 'XREM')}
{_item_widget('Pilot remaining', '18', 'xiqse.pilot.remaining', 'XPIL')}
{_item_widget('Navigator remaining', '36', 'xiqse.nav.remaining', 'XNAV')}
{_item_widget('NAC census', '54', 'xiqse.nac.ok', 'XNOK')}
                - type: svggraph
                  name: Pilot used
                  y: '4'
                  width: '36'
                  height: '6'
                  fields:
                    - type: STRING
                      name: ds.0.color.0
                      value: 2774A4
                    - type: INTEGER
                      name: ds.0.dataset_type
                      value: '0'
                    - type: ITEM
                      name: ds.0.itemids.0
                      value:
                        host: {TPL}
                        key: xiqse.pilot.used
                    - type: STRING
                      name: reference
                      value: XPILG
                    - type: INTEGER
                      name: legend
                      value: '1'
                - type: svggraph
                  name: Navigator used
                  x: '36'
                  y: '4'
                  width: '36'
                  height: '6'
                  fields:
                    - type: STRING
                      name: ds.0.color.0
                      value: E68931
                    - type: INTEGER
                      name: ds.0.dataset_type
                      value: '0'
                    - type: ITEM
                      name: ds.0.itemids.0
                      value:
                        host: {TPL}
                        key: xiqse.nav.used
                    - type: STRING
                      name: reference
                      value: XNAVG
                    - type: INTEGER
                      name: legend
                      value: '1'
        - uuid: {U['dash_engines']}
          name: Engines
          pages:
            - name: Overview
              widgets:
{_item_widget('Engines', '0', 'xiqse.engine.count', 'XENG')}
{_item_widget('Version', '18', 'xiqse.nbi.version', 'XVER')}
{_item_widget('Uptime', '36', 'xiqse.nbi.uptime', 'XUPT')}
                - type: problems
                  name: Problems
                  x: '54'
                  width: '18'
                  height: '4'
                  fields:
                    - type: STRING
                      name: reference
                      value: XEPRB
                    - type: INTEGER
                      name: show
                      value: '3'
{honeycomb}
{radius_h}
"""


def render_nac() -> str:
    return f"""zabbix_export:
  version: '7.0'
  template_groups:
    - uuid: {GROUP_UUID}
      name: Templates/Network devices
  templates:
    - uuid: {U['nac_template']}
      template: {NAC}
      name: {NAC}
      description: |
        ExtremeControl engine companion. ICMP and Linux agent stay on the VM
        path — this template does not nest ICMP Ping and does not speak RADIUS.
        FreeRADIUS down is ticketed from XIQ-SE Observability engine LLD.
        Portal TCP 8444 stays disabled until opted in.

        Operator page: zabbix/07-extreme-control.md.
        Refresh with configure_nbxsync_network.py --apply-xiqse.
      groups:
        - name: Templates/Network devices
      macros:
        - macro: '{{$NAC.PORTAL.PORT}}'
          value: '8444'
          description: Captive portal / admin HTTPS. Not RADIUS 1812.
        - macro: '{{$NAC.PORTAL.CONTROL}}'
          value: '0'
          description: Ticket portal TCP down. Default off — not auth.
      items:
        - uuid: {U['nac_tcp']}
          name: ExtremeControl portal TCP
          type: SIMPLE
          key: 'net.tcp.service[tcp,,{{$NAC.PORTAL.PORT}}]'
          delay: 1m
          history: 7d
          trends: 365d
          value_type: UNSIGNED
          valuemap:
            name: 'Service state'
          tags:
            - tag: component
              value: portal
          triggers:
            - uuid: {U['nac_tr_tcp']}
              expression: '{{$NAC.PORTAL.CONTROL}}=1 and max(/{NAC}/net.tcp.service[tcp,,{{$NAC.PORTAL.PORT}}],#3)=0'
              name: 'ExtremeControl: portal TCP 8444 down'
              event_name: 'ExtremeControl: portal TCP 8444 down'
              priority: WARNING
              status: DISABLED
              description: |
                Admin/portal port, not RADIUS. Enable {{$NAC.PORTAL.CONTROL}} after a quiet pilot.
              tags:
                - tag: scope
                  value: availability
      tags:
        - tag: class
          value: network
        - tag: target
          value: extremecontrol
      dashboards:
        - uuid: {U['nac_dash']}
          name: Health
          pages:
            - name: Overview
              widgets:
                - type: item
                  name: Portal TCP
                  width: '24'
                  height: '4'
                  fields:
                    - type: ITEM
                      name: itemid.0
                      value:
                        host: {NAC}
                        key: 'net.tcp.service[tcp,,{{$NAC.PORTAL.PORT}}]'
                    - type: INTEGER
                      name: show.0
                      value: '2'
                    - type: INTEGER
                      name: value_bold
                      value: '1'
                    - type: INTEGER
                      name: value_size
                      value: '28'
                - type: problems
                  name: Problems
                  x: '24'
                  width: '48'
                  height: '4'
                  fields:
                    - type: STRING
                      name: reference
                      value: NPROB
                    - type: INTEGER
                      name: show
                      value: '3'
      valuemaps:
        - uuid: {U['nac_vm_svc']}
          name: 'Service state'
          mappings:
            - value: '0'
              newvalue: Down
            - value: '1'
              newvalue: Up
"""


def write_yaml() -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    NAC_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    SE_YAML.write_text(render_se(), encoding='utf-8')
    NAC_YAML.write_text(render_nac(), encoding='utf-8')


if __name__ == '__main__':
    write_yaml()
    print(SE_YAML)
    print(NAC_YAML)
