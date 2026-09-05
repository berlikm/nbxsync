# SAP application collection — use what is already on the host

DNUS / Promonitor is gone. Do not invent a Promonitor REST API and do not
run Groovy on the Zabbix proxy. Every Sensirion SAP HANA and SAP ME host
already has the stack Promonitor was wrapping.

## What is already there

| Already on the box | Use it for |
|---|---|
| SAP Host Agent `/usr/sap/hostctrl` (`sapcontrol`, `saphostctrl`) | Instance list + process list + CCMS alerts |
| sapstartsrv HTTP `5{NN}13` / HTTPS `5{NN}14` | Same SOAP (`urn:SAPControl`) if the CLI needs sudo |
| Zabbix agent :10050 (CG **SAP Agent+SNMP**) | Local UserParameter — no extra hop, no `{HOST.CONN}` |
| SNMPv3 `SAPUSER` MD5/DES | Host IF / UCD / filesystems only (SH01 probe: Linux Net-SNMP) |
| Linux by Zabbix agent | CPU cores, disk IO, IP / TCP-UDP. Do not duplicate those keys |
| ICMP Ping on the SAP CG | Ping. Do not nest `icmpping` here |
| `web.certificate.get` | ICM / HTTPS leaf expiry |

`--apply-sap` cannot push the UserParameter. Copy the script and the
agent snippet onto each SAP host, then HostSync.

| File | Install on the SAP host |
|---|---|
| [`../../externalscripts/sap_sensirion.py`](../../externalscripts/sap_sensirion.py) | `/usr/lib/zabbix/externalscripts/sap_sensirion.py` (0755) |
| [`../../userparameters/sap_sensirion.conf`](../../userparameters/sap_sensirion.conf) | `/etc/zabbix/zabbix_agentd.d/sap_sensirion.conf` |

Agent `Timeout=15`. sudoers (no password in the repo):

```
Defaults:zabbix !requiretty
zabbix ALL=(sapadm) NOPASSWD: /usr/sap/hostctrl/exe/sapcontrol, /usr/sap/hostctrl/exe/saphostctrl
```

Check on the host: `zabbix_agentd -t 'sap.sensirion[json,,]'`.

## Think like Basis: HANA vs ME vs ABAP

**`CH-STA-P-SH01` is a HANA box.** `GetProcessList` is the real instance
status: `hdbdaemon`, `hdbnameserver`, `hdbindexserver`, … GREEN/YELLOW = up,
GRAY/RED = down. Host RAM/CPU from SNMP is **not** HANA allocation. This
collector does **not** log on with `hdbsql` — we have no HANA SQL contract.

**SAP ME** is NetWeaver Java (and sometimes ABAP in front). Instance status
is `jstart` / `jcontrol` (and `disp+work` when an ABAP stack is on the same
host). `WinProcessStats_jstart` on ch-sta-p-as02 / ch-sta-d-as01 is the
Windows AS Java stub — not this pack.

**RFC status** here is the **gateway process** (`gwrd`), not SM59 destination
health. A HANA-only or Java-only instance has no `gwrd`; the item is 1 when
the instance is up.

**CCMS `GetAlerts`** is how Promonitor often filled ST22 / IDoc / job /
lock / qRFC / spool / syslog / tRFC / update **when those CCMS nodes
exist**. On a HANA appliance they usually do not — counts stay 0. That is
honest, not a failed poll. Those named LM rows are **not** RFC_READ_TABLE
and not SM13/SM21/SM37/SM58/SM12/EDIDS until someone gives a real SAP
account and a written RFC/`hdbsql` contract.

## Macros

| Macro | Default | Meaning |
|---|---|---|
| `{$SAP.INSTANCE}` | empty | sapstartsrv instance number. Empty = `saphostctrl ListInstances`, then 00/01/02 |
| `{$SAP.SID}` | empty | Filter ListInstances (HDB, MEP, …) |
| `{$SAP.CONTROL.HOST}` | empty | localhost. Only set if sapcontrol must talk to another hostname on the box |
| `{$SAP.APP.CONTROL}` | 0 | 1 tickets heartbeat / thresholds after Latest data is quiet |

Master item: `sap.sensirion[json,{$SAP.INSTANCE},{$SAP.SID},{$SAP.CONTROL.HOST}]`.
Dependents keep the LM `sap.app.*` keys.

## Operator order

1. Install Host Agent UserParameter on the canary (`CH-STA-P-SH01`).
2. `configure_nbxsync_network.py --apply-sap` (no zerotouch, no fleet HostSync).
3. Targeted HostSync of `CH-STA-P-SH01` if it exists and is not onboarding.
4. Confirm Latest data: heartbeat 1, `kind` in the JSON is `hana` on SH01.
5. Set `{$SAP.CERT.HOST}` to the ICM / HTTPS name; then `{$SAP.CERT.CONTROL}=1`.
6. Only then `{$SAP.APP.CONTROL}=1`.
