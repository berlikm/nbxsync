# SAP collection — openSUSE HANA vs Windows ME

DNUS / Promonitor is gone. The estate is two operating systems. Do not put
Linux Net-SNMP (UCD `2021`) on Windows ME, and do not put `jstart.exe` on
openSUSE HANA.

| Role | OS | Template | OS agent (already) | Application |
|---|---|---|---|---|
| **SAP HANA** | openSUSE | `SAP template from Sensirion` | Linux by Zabbix agent (SUSE matches the Linux rule) | `sapcontrol` via Python UserParameter (`/usr/sap/hostctrl`) |
| **SAP ME** | Windows | `SAP ME from Sensirion` | Windows by Zabbix agent | `sapcontrol.exe` via PowerShell + `proc.num[jstart.exe]` |

CG **SAP Agent+SNMP** stays one dual-plane CG (Agent :10050 + `SAPUSER`
MD5/DES) on both roles. ICMP Ping stays on that CG. The SNMP interface on
ME is unused until someone walks a Windows ME box — do not poll UCD there.

`--apply-sap` cannot push UserParameters. HostSync only `CH-STA-P-SH01`.

## SAP HANA — openSUSE

Canary `CH-STA-P-SH01` is Linux Net-SNMP (`1.3.6.1.4.1.8072.3.2.10`). Host
IF / UCD / filesystems belong on the HANA template. Host RAM/CPU is **not**
HANA allocation. No `hdbsql`.

| File | Install on the HANA host |
|---|---|
| [`../../externalscripts/sap_sensirion.py`](../../externalscripts/sap_sensirion.py) | `/usr/lib/zabbix/externalscripts/sap_sensirion.py` (0755) |
| [`../../userparameters/sap_sensirion.conf`](../../userparameters/sap_sensirion.conf) | `/etc/zabbix/zabbix_agentd.d/sap_sensirion.conf` |

Agent `Timeout=15`. sudoers:

```
Defaults:zabbix !requiretty
zabbix ALL=(sapadm) NOPASSWD: /usr/sap/hostctrl/exe/sapcontrol, /usr/sap/hostctrl/exe/saphostctrl
```

`zabbix_agentd -t 'sap.sensirion[json,,]'` — JSON `kind` should be `hana`.

## SAP ME — Windows AS Java

`ch-sta-p-as02` / `ch-sta-d-as01` are the LM Windows `jstart` hosts. That
**is** SAP ME, not a leftover stub. OS CPU/memory/disks stay on **Windows by
Zabbix agent**. LM `DataSource_batchscript.powershell` was the Windows
collector vehicle; the replacement is a PowerShell UserParameter calling
the Host Agent that is already on a NetWeaver Java box:

`C:\Program Files\SAP\hostctrl\exe\sapcontrol.exe`

| File | Install on the ME host |
|---|---|
| [`../../externalscripts/sap_sensirion.ps1`](../../externalscripts/sap_sensirion.ps1) | `C:\Program Files\Zabbix Agent\externalscripts\sap_sensirion.ps1` |
| [`../../userparameters/sap_sensirion.win.conf`](../../userparameters/sap_sensirion.win.conf) | agent UserParameter include dir |

`zabbix_agentd.exe -t sap.sensirion[json,,]` — JSON `kind` should be `java`.
`proc.num[jstart.exe]` is the LM Windows process check.

ME Java has no ST22 / IDoc / qRFC / SM13. Those `sap.app.*` counts stay 0
unless CCMS nodes exist. Instance status is `jstart` / `jcontrol`. RFC is
1 while the instance is up (no `gwrd`).

## Macros

Same application / cert / port macros on both templates. HANA also has the
UCD / IF / FS macros. `{$SAP.APP.CONTROL}=0` until Latest data is quiet.

## Operator order

1. HANA canary: install the Linux UserParameter on `CH-STA-P-SH01`.
2. `--apply-sap` (no zerotouch, no fleet HostSync).
3. Confirm HANA Latest data; set `{$SAP.CERT.HOST}`; then `{$SAP.APP.CONTROL}=1` on HANA only.
4. ME: install the PowerShell snippet on as02/as01, HostSync those hosts
   separately, then enable CONTROL on ME.
