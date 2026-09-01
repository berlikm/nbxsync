#!/usr/bin/env python3
"""Render ExtremeCloud IQ by HTTP YAML from the JS contract."""

from __future__ import annotations

from xiq_cloud import CLOUD_YAML, TEMPLATE_DIR, account_script, ops_script, yaml_literal

GROUP_UUID = '36bff6c29af64692839d077febfc7079'
TPL = 'ExtremeCloud IQ by HTTP'

U = {
    'template': 'ad8fa6aebeb2489fab8fa63e4977f173',
    'vm_api': '4dedf31c9dc04797ac23833e9653c7b1',
    'vm_bool': '6d390939e8f34570a36f13cb8111b727',
    'vm_tri': '9f224eff307c44c5aacf80bfc65f4a48',
    'item_account': '9f5bf4c486894e278ddb2fa4b6c14fd6',
    'item_ops': 'bf15d2bfcc4b4fda81d7635eb5cee8e7',
    'item_avail': '8262680c7331464fbc3d861133b09dd7',
    'item_error': '6cdf1c9234ee49aa8fee09796a4101d4',
    'item_customer': 'f55eba41a0e344fa910bcdd95eddf661',
    'item_expired': 'b4be98e8b1d848cd8d98f9ae71d52315',
    'item_vhm_status': 'af03307a07ec43399120caef9f3809bb',
    'item_vhm_active': 'ed100683dc734eb39da1b14c1e74fc12',
    'item_token_ttl': '89ccbc2c3f4d4fb49aef9572b4c89026',
    'item_token_known': '7795c8fe986e44738adb14a31ae269c4',
    'item_lic_count': '15b65a478de941069c63a2bd99cd70cd',
    'item_lic_types': '5a9c7d0350d24e3597fad04a937d9614',
    'item_pilot_present': '009308693c20488bbb2568114b392c09',
    'item_pilot_have': '5327684014914b1397f4231800ca95cd',
    'item_pilot_activated': '90b0eca4092e4aeb83d330fbcffdfb35',
    'item_pilot_available': 'e3759dd29ec14ce08437c7372361b2b7',
    'item_pilot_expire': 'd5dc911bfdb14ec2816ec6e134c7307e',
    'item_nav_present': '9a99f862adff48bd91f06131bd8986b5',
    'item_nav_have': 'd0ac704a97a441bbae179b3f05e59090',
    'item_nav_activated': '44c75ed761df4ef9addfa360faa2af13',
    'item_nav_available': 'f5a76ab6299c4b3ebc619127b68e27f2',
    'item_nav_expire': '7080fb1e27184efaa79a9139d5e6b48c',
    'item_copilot_have': 'ffc00cae09584eedbc681138516251e0',
    'item_copilot_activated': 'edba52989c664cd0b5e714fe3d940413',
    'item_copilot_available': '5565207f8fb6421c9d187f2ee1ad4aeb',
    'item_nac_present': '4527d21542224ef597cbaecfc5a55e29',
    'item_nac_have': '533989a97666423e912ba0b657670f90',
    'item_nac_activated': '8e90956d790849e08c85d35e9a31c46a',
    'item_nac_available': '2b04d95d198145ecac1f0dee4f438af6',
    'item_backup_time': '2e807ff790594c0a83e517b6cd8889d4',
    'item_backup_age': 'eff20879d95c45849c4d6654d74f708f',
    'item_backup_name': '547fc20f57244f428e486ab426733bff',
    'item_dev_total': '29be542eb8de4212b3890ecc4fff0c59',
    'item_dev_managed': '9bef8aaa071842979c32067d9e5222cc',
    'item_dev_connected': '1eb40a59beab4fe1b1b5c76e55c7d24a',
    'item_dev_disconnected': '2fdcba083a5648af966f680f3d550a47',
    'item_ops_ok': '1b106016b63343008f8b88aaeefeb548',
    'item_ops_error': '967ab4a6405348dea9007621150477ad',
    'item_unsupported': 'a8b300c439144f03b0d1f3e46e07c74e',
    'tr_avail': '3adb3c4d77ef468a80b4a5cdb0ff4c3c',
    'tr_nodata': 'a93206e4776844caa1d7ceb840d83f01',
    'tr_token': '03c7f947346742e0a862bd36e8fb4357',
    'tr_expired': '6691af1eb854461e8af9ca7ba218a17e',
    'tr_vhm': '49847026b5cb4e7baa1cb3f613ecf99f',
    'tr_zero_lic': 'f1c9a41478f849e18b838c7f9dd2a60f',
    'tr_backup': 'c092eaa715604aff8591e1efa82a672b',
    'tr_pilot_avail': '018bdbe01ccb4e928c6f4f8b4dc53500',
    'tr_nav_avail': '254756d46274477f81bb5c132f68fdf6',
    'tr_pilot_exp': '957bea2ecb504de3bd50997ed7b67114',
    'tr_nav_exp': 'c0e2fefdf2fe4a1eb4b739f597e05016',
    'tr_unsup': '249053fe1a1b4315a1db9c5ebe5a8031',
    'dash_health': '1edf21b1f9384d61a6a709c20a1f5c79',
    'graph_pilot': '0f3f3f08f50c460b9a309f0c6f081407',
    'graph_backup': '819ce94036fe43988b2cc05ff01c73c2',
}

TAGS_API = """      tags:
        - tag: component
          value: xiq-cloud
        - tag: scope
          value: health"""
TAGS_LIC = """      tags:
        - tag: component
          value: license
        - tag: scope
          value: health"""
TAGS_OPS = """      tags:
        - tag: component
          value: xiq-cloud
        - tag: scope
          value: ops"""


def bump(text: str, spaces: int = 4) -> str:
    pad = ' ' * spaces
    return '\n'.join(pad + line if line else line for line in text.split('\n'))


def _params() -> str:
    return """      parameters:
        - name: url
          value: '{$XIQ.CLOUD.API.URL}'
        - name: token
          value: '{$XIQ.CLOUD.API.TOKEN}'"""


def _script_item(uuid: str, name: str, key: str, delay: str, timeout: str, script: str, extra: str = '', tags: str = TAGS_API) -> str:
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
{_params()}
{extra}{tags}"""


def _dep(
    uuid: str,
    name: str,
    key: str,
    master: str,
    jpath: str,
    value_type: str,
    units: str = '',
    extra: str = '',
    tags: str = TAGS_API,
) -> str:
    units_l = ("\n      units: '" + units + "'") if units else ''
    trends = "      trends: 365d\n" if value_type in {'FLOAT', 'UNSIGNED'} else "      trends: '0'\n"
    return f"""    - uuid: {uuid}
      name: {name}
      type: DEPENDENT
      key: {key}
      delay: '0'
      history: 7d
{trends}      value_type: {value_type}{units_l}
      preprocessing:
        - type: JSONPATH
          parameters:
            - '{jpath}'
      master_item:
        key: {master}
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


def _macros() -> str:
    rows = [
        ('{$XIQ.CLOUD.API.URL}', 'https://api.extremecloudiq.com', 'ExtremeCloud IQ REST base. TLS verify stays on.'),
        ('{$XIQ.CLOUD.API.TOKEN}', '', 'Long-lived Bearer from POST /auth/apitoken (ops creates it once). Put on CG ExtremeCloud IQ API, not the host.', 'SECRET_TEXT'),
        ('{$XIQ.CLOUD.DATA.TIMEOUT}', '30s', 'Account SCRIPT timeout (viq + vhm + token info).'),
        ('{$XIQ.CLOUD.OPS.TIMEOUT}', '45s', 'Ops SCRIPT timeout (backup grid + device stats).'),
        ('{$XIQ.CLOUD.BACKUP.MAX}', '691200', 'Ticket last CONFIG backup age at or above this many seconds (8d).'),
        ('{$XIQ.CLOUD.TOKEN.WARN}', '14d', 'Warning when token TTL is below this.'),
        ('{$XIQ.CLOUD.EXPIRY.WARN}', '30d', 'Warning when a matched Pilot/Navigator expire_date is within this window.'),
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


def _dashboards() -> str:
    return f"""      dashboards:
        - uuid: {U['dash_health']}
          name: Health
          pages:
            - name: Overview
              widgets:
{_item_widget('API', '0', 'xiq.cloud.available', 'CAPI')}
{_item_widget('Pilot available', '18', 'xiq.cloud.pilot.available', 'CPAV')}
{_item_widget('Pilot have', '36', 'xiq.cloud.pilot.have', 'CPHV')}
{_item_widget('Pilot activated', '54', 'xiq.cloud.pilot.activated', 'CPAC')}
                - type: problems
                  name: Problems
                  y: '4'
                  width: '72'
                  height: '4'
                  fields:
                    - type: STRING
                      name: reference
                      value: CPROB
                    - type: INTEGER
                      name: show
                      value: '3'
                - type: svggraph
                  name: Pilot Cloud seats
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
                        key: xiq.cloud.pilot.available
                    - type: STRING
                      name: reference
                      value: CPILG
                    - type: INTEGER
                      name: legend
                      value: '1'
                - type: svggraph
                  name: Last CONFIG backup age
                  x: '36'
                  y: '8'
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
                        key: xiq.cloud.backup.age
                    - type: STRING
                      name: reference
                      value: CBKUP
                    - type: INTEGER
                      name: legend
                      value: '1'
            - name: Licenses
              widgets:
{_item_widget('Pilot have', '0', 'xiq.cloud.pilot.have', 'LPHV')}
{_item_widget('Pilot activated', '18', 'xiq.cloud.pilot.activated', 'LPAC')}
{_item_widget('Pilot available', '36', 'xiq.cloud.pilot.available', 'LPAV')}
{_item_widget('Navigator available', '54', 'xiq.cloud.nav.available', 'LNAV')}
"""


def render_cloud() -> str:
    account = _script_item(
        U['item_account'],
        'ExtremeCloud IQ account snapshot',
        'xiq.cloud.account',
        '5m',
        '{$XIQ.CLOUD.DATA.TIMEOUT}',
        account_script(),
        extra="      description: |\n        GET /account/viq + /account/vhm/status + /auth/apitoken/info. Bearer only. Does not POST /auth/apitoken.\n",
    )
    ops = _script_item(
        U['item_ops'],
        'ExtremeCloud IQ ops snapshot',
        'xiq.cloud.ops',
        '15m',
        '{$XIQ.CLOUD.OPS.TIMEOUT}',
        ops_script(),
        extra="      description: |\n        GET /backup/history/grid and /devices/stats. Census only — no disconnected ticket, query only.\n",
        tags=TAGS_OPS,
    )

    avail_tr = _trigger(
        U['tr_avail'],
        f'min(/{TPL}/xiq.cloud.available,15m)=0',
        'ExtremeCloud IQ: API unexpected response',
        'AVERAGE',
        'Bearer token or api.extremecloudiq.com failed. Onboarding and Portal seats go dark. RADIUS still works. Does not depend on SE NBI.',
    )
    nodata_tr = _trigger(
        U['tr_nodata'],
        f'nodata(/{TPL}/xiq.cloud.account,20m)=1',
        'ExtremeCloud IQ: no API data for 20m',
        'AVERAGE',
        'Account SCRIPT produced no values. Token, proxy egress, or Extreme outage.',
    )
    token_tr = _trigger(
        U['tr_token'],
        f'last(/{TPL}/xiq.cloud.available)=1 and last(/{TPL}/xiq.cloud.token.known)=1 and last(/{TPL}/xiq.cloud.token.ttl)<{{$XIQ.CLOUD.TOKEN.WARN}}',
        'ExtremeCloud IQ: API token expires soon',
        'WARNING',
        'GET /auth/apitoken/info TTL below {$XIQ.CLOUD.TOKEN.WARN}. Dayside rotate. Do not POST a new token from Zabbix.',
    )
    expired_tr = _trigger(
        U['tr_expired'],
        f'last(/{TPL}/xiq.cloud.available)=1 and last(/{TPL}/xiq.cloud.expired)=1',
        'ExtremeCloud IQ: VIQ expired',
        'AVERAGE',
        'GET /account/viq expired=true. Connected-mode devices go unmanaged. Not a switch ICMP.',
    )
    vhm_tr = _trigger(
        U['tr_vhm'],
        f'last(/{TPL}/xiq.cloud.available)=1 and last(/{TPL}/xiq.cloud.vhm.active)=0',
        'ExtremeCloud IQ: VHM not ACTIVE',
        'AVERAGE',
        'GET /account/vhm/status is not ACTIVE_STATUS / ACTIVE. Unknown (2) stays silent.',
    )
    zero_tr = _trigger(
        U['tr_zero_lic'],
        f'last(/{TPL}/xiq.cloud.available)=1 and last(/{TPL}/xiq.cloud.license.count)=0',
        'ExtremeCloud IQ: no license rows',
        'AVERAGE',
        'VIQ answered but licenses[] is empty. Token missing licenses:r, or Portal unlink.',
    )
    backup_tr = _trigger(
        U['tr_backup'],
        f'last(/{TPL}/xiq.cloud.backup.time)>0 and last(/{TPL}/xiq.cloud.backup.age)>={{$XIQ.CLOUD.BACKUP.MAX}}',
        'ExtremeCloud IQ: last CONFIG backup stale',
        'AVERAGE',
        'Newest CONFIG row on GET /backup/history/grid is older than {$XIQ.CLOUD.BACKUP.MAX}. Empty grid stays silent until a first backup exists.',
    )
    pilot_avail_tr = _trigger(
        U['tr_pilot_avail'],
        f'last(/{TPL}/xiq.cloud.available)=1 and last(/{TPL}/xiq.cloud.pilot.present)=1 and last(/{TPL}/xiq.cloud.pilot.have)>0 and last(/{TPL}/xiq.cloud.pilot.available)=0',
        'ExtremeCloud IQ: Pilot Cloud available is 0',
        'WARNING',
        'Cannot onboard. Cloud available from VIQ licenses[], never SE inventory and never Portal total minus SE used.',
    )
    nav_avail_tr = _trigger(
        U['tr_nav_avail'],
        f'last(/{TPL}/xiq.cloud.available)=1 and last(/{TPL}/xiq.cloud.nav.present)=1 and last(/{TPL}/xiq.cloud.nav.have)>0 and last(/{TPL}/xiq.cloud.nav.available)=0',
        'ExtremeCloud IQ: Navigator Cloud available is 0',
        'WARNING',
        'Cannot onboard a Navigator-tier device. Cloud available, not SE inventory.',
    )
    pilot_exp_tr = _trigger(
        U['tr_pilot_exp'],
        f'last(/{TPL}/xiq.cloud.available)=1 and last(/{TPL}/xiq.cloud.pilot.present)=1 and last(/{TPL}/xiq.cloud.pilot.have)>0 and last(/{TPL}/xiq.cloud.pilot.expire)>0 and (last(/{TPL}/xiq.cloud.pilot.expire)-now())<{{$XIQ.CLOUD.EXPIRY.WARN}}',
        'ExtremeCloud IQ: Pilot SKU expires soon',
        'WARNING',
        'Earliest matched Pilot expire_date is within {$XIQ.CLOUD.EXPIRY.WARN}.',
    )
    nav_exp_tr = _trigger(
        U['tr_nav_exp'],
        f'last(/{TPL}/xiq.cloud.available)=1 and last(/{TPL}/xiq.cloud.nav.present)=1 and last(/{TPL}/xiq.cloud.nav.have)>0 and last(/{TPL}/xiq.cloud.nav.expire)>0 and (last(/{TPL}/xiq.cloud.nav.expire)-now())<{{$XIQ.CLOUD.EXPIRY.WARN}}',
        'ExtremeCloud IQ: Navigator SKU expires soon',
        'WARNING',
        'Earliest matched Navigator expire_date is within {$XIQ.CLOUD.EXPIRY.WARN}.',
    )
    unsup = _trigger(
        U['tr_unsup'],
        f'last(/{TPL}/zabbix[host,,items_unsupported])>0',
        'ExtremeCloud IQ: unsupported items present',
        'AVERAGE',
        'Schema field missing or SCRIPT error. Snapshot always stringifies zeros so Cloud 7.0 dependents stay supported.',
    )

    avail_item = _dep(
        U['item_avail'],
        'ExtremeCloud IQ API available',
        'xiq.cloud.available',
        'xiq.cloud.account',
        '$.ok',
        'UNSIGNED',
        extra=f'      valuemap:\n        name: ExtremeCloud IQ API\n      triggers:\n{avail_tr}\n{nodata_tr}\n',
    )
    error_item = _dep(U['item_error'], 'ExtremeCloud IQ last error', 'xiq.cloud.error', 'xiq.cloud.account', '$.error', 'TEXT')
    customer_item = _dep(U['item_customer'], 'ExtremeCloud IQ customer id', 'xiq.cloud.customer', 'xiq.cloud.account', '$.customerId', 'TEXT')
    expired_item = _dep(
        U['item_expired'],
        'ExtremeCloud IQ VIQ expired',
        'xiq.cloud.expired',
        'xiq.cloud.account',
        '$.expired',
        'UNSIGNED',
        extra=f'      valuemap:\n        name: ExtremeCloud IQ bool\n      triggers:\n{expired_tr}\n',
    )
    vhm_status = _dep(U['item_vhm_status'], 'ExtremeCloud IQ VHM status', 'xiq.cloud.vhm.status', 'xiq.cloud.account', '$.vhmStatus', 'TEXT')
    vhm_active = _dep(
        U['item_vhm_active'],
        'ExtremeCloud IQ VHM active',
        'xiq.cloud.vhm.active',
        'xiq.cloud.account',
        '$.vhmActive',
        'UNSIGNED',
        extra=f'      valuemap:\n        name: ExtremeCloud IQ tri-state\n      triggers:\n{vhm_tr}\n',
    )
    token_ttl = _dep(
        U['item_token_ttl'],
        'ExtremeCloud IQ API token TTL',
        'xiq.cloud.token.ttl',
        'xiq.cloud.account',
        '$.tokenTtl',
        'UNSIGNED',
        units='s',
        extra=f'      triggers:\n{token_tr}\n',
    )
    token_known = _dep(
        U['item_token_known'],
        'ExtremeCloud IQ API token info ok',
        'xiq.cloud.token.known',
        'xiq.cloud.account',
        '$.tokenKnown',
        'UNSIGNED',
        extra='      valuemap:\n        name: ExtremeCloud IQ API\n',
    )
    lic_count = _dep(
        U['item_lic_count'],
        'ExtremeCloud IQ license row count',
        'xiq.cloud.license.count',
        'xiq.cloud.account',
        '$.licenseCount',
        'UNSIGNED',
        extra=f'      triggers:\n{zero_tr}\n',
        tags=TAGS_LIC,
    )
    lic_types = _dep(
        U['item_lic_types'],
        'ExtremeCloud IQ license_type values',
        'xiq.cloud.license.types',
        'xiq.cloud.account',
        '$.licenseTypes',
        'TEXT',
        extra="      description: |\n        Joined unique licenses[].license_type for Latest data canary. Do not key LLD on this until the Portal SKUs are proven.\n",
        tags=TAGS_LIC,
    )
    pilot_present = _dep(U['item_pilot_present'], 'Pilot Cloud present', 'xiq.cloud.pilot.present', 'xiq.cloud.account', '$.pilotPresent', 'UNSIGNED', extra='      valuemap:\n        name: ExtremeCloud IQ bool\n', tags=TAGS_LIC)
    pilot_have = _dep(U['item_pilot_have'], 'Pilot Cloud have', 'xiq.cloud.pilot.have', 'xiq.cloud.account', '$.pilotHave', 'UNSIGNED', extra="      description: |\n        Sum of matching licenses[].devices (Portal 581 class). Not SE network.devices.\n", tags=TAGS_LIC)
    pilot_activated = _dep(U['item_pilot_activated'], 'Pilot Cloud activated', 'xiq.cloud.pilot.activated', 'xiq.cloud.account', '$.pilotActivated', 'UNSIGNED', extra="      description: |\n        Cloud consume including APs. Never subtract SE 320 from this.\n", tags=TAGS_LIC)
    pilot_available = _dep(
        U['item_pilot_available'],
        'Pilot Cloud available',
        'xiq.cloud.pilot.available',
        'xiq.cloud.account',
        '$.pilotAvailable',
        'UNSIGNED',
        extra="      description: |\n        Cloud remaining. This is Portal available, not Portal total minus SE used.\n      triggers:\n"
        + f'{pilot_avail_tr}\n',
        tags=TAGS_LIC,
    )
    pilot_expire = _dep(
        U['item_pilot_expire'],
        'Pilot Cloud earliest expire',
        'xiq.cloud.pilot.expire',
        'xiq.cloud.account',
        '$.pilotExpire',
        'UNSIGNED',
        units='unixtime',
        extra=f'      triggers:\n{pilot_exp_tr}\n',
        tags=TAGS_LIC,
    )
    nav_present = _dep(U['item_nav_present'], 'Navigator Cloud present', 'xiq.cloud.nav.present', 'xiq.cloud.account', '$.navPresent', 'UNSIGNED', extra='      valuemap:\n        name: ExtremeCloud IQ bool\n', tags=TAGS_LIC)
    nav_have = _dep(U['item_nav_have'], 'Navigator Cloud have', 'xiq.cloud.nav.have', 'xiq.cloud.account', '$.navHave', 'UNSIGNED', tags=TAGS_LIC)
    nav_activated = _dep(U['item_nav_activated'], 'Navigator Cloud activated', 'xiq.cloud.nav.activated', 'xiq.cloud.account', '$.navActivated', 'UNSIGNED', tags=TAGS_LIC)
    nav_available = _dep(
        U['item_nav_available'],
        'Navigator Cloud available',
        'xiq.cloud.nav.available',
        'xiq.cloud.account',
        '$.navAvailable',
        'UNSIGNED',
        extra=f'      triggers:\n{nav_avail_tr}\n',
        tags=TAGS_LIC,
    )
    nav_expire = _dep(
        U['item_nav_expire'],
        'Navigator Cloud earliest expire',
        'xiq.cloud.nav.expire',
        'xiq.cloud.account',
        '$.navExpire',
        'UNSIGNED',
        units='unixtime',
        extra=f'      triggers:\n{nav_exp_tr}\n',
        tags=TAGS_LIC,
    )
    copilot_have = _dep(U['item_copilot_have'], 'Copilot Cloud have', 'xiq.cloud.copilot.have', 'xiq.cloud.account', '$.copilotHave', 'UNSIGNED', extra="      description: |\n        Collect only. Copilot exhaust stays off until a later canary.\n", tags=TAGS_LIC)
    copilot_activated = _dep(U['item_copilot_activated'], 'Copilot Cloud activated', 'xiq.cloud.copilot.activated', 'xiq.cloud.account', '$.copilotActivated', 'UNSIGNED', tags=TAGS_LIC)
    copilot_available = _dep(U['item_copilot_available'], 'Copilot Cloud available', 'xiq.cloud.copilot.available', 'xiq.cloud.account', '$.copilotAvailable', 'UNSIGNED', tags=TAGS_LIC)
    nac_present = _dep(
        U['item_nac_present'],
        'NAC Cloud present',
        'xiq.cloud.nac.present',
        'xiq.cloud.account',
        '$.nacPresent',
        'UNSIGNED',
        extra="      description: |\n        1 if a licenses[] row matched NAC. Portal 3000 may live only on /nac-entitlements/stats — do not ticket available=0 from this item.\n      valuemap:\n        name: ExtremeCloud IQ bool\n",
        tags=TAGS_LIC,
    )
    nac_have = _dep(U['item_nac_have'], 'NAC Cloud have', 'xiq.cloud.nac.have', 'xiq.cloud.account', '$.nacHave', 'UNSIGNED', extra="      description: |\n        Collect only. NAC consume is SE 24h unique MACs, not this column.\n", tags=TAGS_LIC)
    nac_activated = _dep(U['item_nac_activated'], 'NAC Cloud activated', 'xiq.cloud.nac.activated', 'xiq.cloud.account', '$.nacActivated', 'UNSIGNED', tags=TAGS_LIC)
    nac_available = _dep(
        U['item_nac_available'],
        'NAC Cloud available',
        'xiq.cloud.nac.available',
        'xiq.cloud.account',
        '$.nacAvailable',
        'UNSIGNED',
        extra="      description: |\n        Collect only until /nac-entitlements/stats is canaried. No trigger.\n",
        tags=TAGS_LIC,
    )
    backup_time = _dep(
        U['item_backup_time'],
        'ExtremeCloud IQ last CONFIG backup',
        'xiq.cloud.backup.time',
        'xiq.cloud.ops',
        '$.lastConfigBackup',
        'UNSIGNED',
        units='unixtime',
        tags=TAGS_OPS,
    )
    backup_age = _dep(
        U['item_backup_age'],
        'ExtremeCloud IQ last CONFIG backup age',
        'xiq.cloud.backup.age',
        'xiq.cloud.ops',
        '$.lastConfigBackupAge',
        'UNSIGNED',
        units='s',
        extra=f'      triggers:\n{backup_tr}\n',
        tags=TAGS_OPS,
    )
    backup_name = _dep(U['item_backup_name'], 'ExtremeCloud IQ last CONFIG backup name', 'xiq.cloud.backup.name', 'xiq.cloud.ops', '$.lastConfigBackupName', 'TEXT', tags=TAGS_OPS)
    dev_total = _dep(U['item_dev_total'], 'ExtremeCloud IQ device total', 'xiq.cloud.devices.total', 'xiq.cloud.ops', '$.deviceTotal', 'UNSIGNED', extra="      description: |\n        GET /devices/stats census. No disconnected ticket — 01/02 own the box.\n", tags=TAGS_OPS)
    dev_managed = _dep(U['item_dev_managed'], 'ExtremeCloud IQ device managed', 'xiq.cloud.devices.managed', 'xiq.cloud.ops', '$.deviceManaged', 'UNSIGNED', tags=TAGS_OPS)
    dev_connected = _dep(U['item_dev_connected'], 'ExtremeCloud IQ device connected', 'xiq.cloud.devices.connected', 'xiq.cloud.ops', '$.deviceConnected', 'UNSIGNED', tags=TAGS_OPS)
    dev_disconnected = _dep(
        U['item_dev_disconnected'],
        'ExtremeCloud IQ device disconnected',
        'xiq.cloud.devices.disconnected',
        'xiq.cloud.ops',
        '$.deviceDisconnected',
        'UNSIGNED',
        extra="      description: |\n        Collect only. Do not page — switch/AP ICMP already does.\n",
        tags=TAGS_OPS,
    )
    ops_ok = _dep(U['item_ops_ok'], 'ExtremeCloud IQ ops snapshot ok', 'xiq.cloud.ops.ok', 'xiq.cloud.ops', '$.ok', 'UNSIGNED', extra='      valuemap:\n        name: ExtremeCloud IQ API\n', tags=TAGS_OPS)
    ops_error = _dep(U['item_ops_error'], 'ExtremeCloud IQ ops last error', 'xiq.cloud.ops.error', 'xiq.cloud.ops', '$.error', 'TEXT', tags=TAGS_OPS)
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
        ExtremeCloud IQ VIQ companion on the Site Engine host. SCRIPT HTTPS to
        {{$XIQ.CLOUD.API.URL}} (default https://api.extremecloudiq.com). Long-lived
        Bearer {{$XIQ.CLOUD.API.TOKEN}}. Does not nest ICMP. Does not nest XIQ-SE
        Observability. Does not POST /auth/apitoken. Does not fold into NBI.

        Operator page: zabbix/08-extremecloud-iq.md.
        Refresh with configure_nbxsync_network.py --apply-xiq-cloud.
      groups:
        - name: Templates/Network devices
{_macros()}
      items:
{bump(account)}
{bump(ops)}
{bump(avail_item)}
{bump(error_item)}
{bump(customer_item)}
{bump(expired_item)}
{bump(vhm_status)}
{bump(vhm_active)}
{bump(token_ttl)}
{bump(token_known)}
{bump(lic_count)}
{bump(lic_types)}
{bump(pilot_present)}
{bump(pilot_have)}
{bump(pilot_activated)}
{bump(pilot_available)}
{bump(pilot_expire)}
{bump(nav_present)}
{bump(nav_have)}
{bump(nav_activated)}
{bump(nav_available)}
{bump(nav_expire)}
{bump(copilot_have)}
{bump(copilot_activated)}
{bump(copilot_available)}
{bump(nac_present)}
{bump(nac_have)}
{bump(nac_activated)}
{bump(nac_available)}
{bump(backup_time)}
{bump(backup_age)}
{bump(backup_name)}
{bump(dev_total)}
{bump(dev_managed)}
{bump(dev_connected)}
{bump(dev_disconnected)}
{bump(ops_ok)}
{bump(ops_error)}
{bump(unsup_item)}
      tags:
        - tag: class
          value: network
        - tag: target
          value: xiq-cloud
{_dashboards()}
      valuemaps:
        - uuid: {U['vm_api']}
          name: ExtremeCloud IQ API
          mappings:
            - value: '0'
              newvalue: Down
            - value: '1'
              newvalue: Up
        - uuid: {U['vm_bool']}
          name: ExtremeCloud IQ bool
          mappings:
            - value: '0'
              newvalue: No
            - value: '1'
              newvalue: Yes
        - uuid: {U['vm_tri']}
          name: ExtremeCloud IQ tri-state
          mappings:
            - value: '0'
              newvalue: No
            - value: '1'
              newvalue: Yes
            - value: '2'
              newvalue: Unknown
"""


def write_yaml() -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    CLOUD_YAML.write_text(render_cloud(), encoding='utf-8')


if __name__ == '__main__':
    write_yaml()
    print(CLOUD_YAML)
