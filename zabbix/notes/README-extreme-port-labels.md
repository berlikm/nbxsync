# Extreme Port Labels — NetBox custom script

`extreme_port_labels.py` computes the expected on-box port label
`CLASS[-SPEED]-ID` from **NetBox cabling**, reads the **live** label off each
Extreme switch, and reports the diff. Optionally it remediates.

The label lands in SNMP `ifAlias`, which is what Zabbix LLD filters on
(`{$NET.IF.IFALIAS.MATCHES}`). A wrong or truncated label silently drops a port
out of — or into — monitoring.

Grammar authority: [`zabbix/reference/port-identity-foundation.md`](../../zabbix/reference/port-identity-foundation.md),
[`zabbix/notes/verified-facts.md`](../../zabbix/notes/verified-facts.md).
This README only adds what those documents leave open: **how the ID is derived
from NetBox topology**, and **which CLI verbs are used**.

---

## 1. Install

NetBox loads every `.py` in `SCRIPTS_ROOT` as a script module, so this is a
single flat file next to the others:

```
Netbox-scripts/
├── extreme_cli_runner.py       # SSH transport — reused, not forked
├── extreme_firmware_upgrade.py
└── extreme_port_labels.py      # this script
```

It reuses the CLI runner's session helpers and credential resolution by loading
the sibling file by path (`importlib`), because NetBox loads each script module
in isolation and a plain `import extreme_cli_runner` is not reliable. If the
runner cannot be loaded the script says so and refuses to open its own SSH
stack.

Same environment variables as the runner — **no secrets in code**:

| Variable | Purpose |
|---|---|
| `EXTREME_VENV_PATH` | venv holding `netmiko` |
| `NBX_NAPALM_EXOS_USERNAME` / `NBX_NAPALM_EXOS_PASSWORD` | EXOS |
| `NBX_NAPALM_VOSS_USERNAME` / `NBX_NAPALM_VOSS_PASSWORD` | VOSS |

Unit tests (pure helpers only, no NetBox required):

```bash
python3 zabbix/notes/test_extreme_port_labels.py
python3 zabbix/notes/test_extreme_port_labels_canary.py
```

The fleet canary is `zabbix/notes/fixtures/port_label_canary.tsv` — every
cabled Extreme port from the NetBox export. The `expected_label` column is
the *old* generator (5-character SPEED slot, floor often dropped); tests
**recompute** and assert length ≤ 20, CLASS, floor kept, and no per-device
collisions. Excel-coerced VOSS ports (`Jan 19`, `01. Jul`, `02. Mär`) are
recovered in `port_label_canary.py` before replay. Rebuild the TSV with
`python3 zabbix/notes/fixtures/build_port_label_canary.py`.

---

## 2. Run

| Field | Meaning |
|---|---|
| **Mode** | `compliance` (default, read-only) or `remediate` |
| **Commit changes** | NetBox's own box. Remediation needs **both** |
| **Canary allowlist** | `device-name::ifname` per line — limits the push |
| **Scope** | site group / site / role / device tag / explicit devices |
| **Platform** | EXOS · VOSS · both |
| **Structural tags** | interface tags meaning "never alert" → expected label `X` |
| **Include admin-down / X·N** | reporting breadth |
| **Also clear EXOS description-string** | off by default (may hold human text) |
| **Fail the job on blocking diffs** | for scheduled compliance runs |

**Scope rule:** cabled ports are evaluated from NetBox topology. A port with **no complete cable path** (nothing, or a patch panel with no far device) cannot derive a far end — it is not remediated. If the box still has a live label, it is reported as `orphan` (inventory drift). Cable the port in NetBox (or admin-down / `X`) before expecting a grammar label.

SSH uses **`oob_ip` first**, then `primary_ip`. Site groups include **nested children**.

Per-port statuses: `ok` · `diff` · `missing` · `too_long` · `forbidden` ·
`description_string_set` · `orphan` · `unreachable` · `applied`.

---

## 3. The ID convention (the "where is this connected" footnote)

The grammar fixes `CLASS[-SPEED]-ID` but deliberately leaves ID as "a
machine-short far-end abbreviation". This is the concrete rule, derived from
what the estate already does.

### 3.1 What the estate already does

Live `show configuration` from production EXOS
(`New folder (3)/scratch/probe-exos-fullcfg-*`):

```
configure ports 1:8 display-string L02-ACCE03_p23
configure ports 1:2 display-string LR44-GFL-DIST01_p23
configure ports 6   display-string GFL-ACPO16
```

Live `show running-config` from production VOSS
(`New folder (3)/scratch/probe_voss_running_config_CH-STA-L26-L02-CORE01.txt`):

```
name "L26-GFL-Di02:29"
name "NNI:L26-Co02:1/24"
```

So engineers here already write *far-end device + far-end port*, already
compress role codes (`Di`, `Co`), and already use `_p<port>`. Two problems:
`:` is **forbidden** on EXOS, and the long forms overflow 20 once a `CLASS-`
prefix is added.

Device names follow `<SITESLUG>-[<LOC>-]<CODE><NN>[-<STACK>]`
(`CH-STA-L50-B01-ACCE01`, `CH-STA-L50-L01-CORE01`, `CH-NKN-G08-L02-CORE01-1`),
which is what makes a deterministic abbreviation possible at all.

### 3.2 The rule

```
ID = [<SCOPE>-]<CODE><NN>[-<STACK>][_p<FARPORT>]
```

| Piece | Source | Example |
|---|---|---|
| `SCOPE` | far-end **location** token when the far end is in the same site, otherwise the far **site** tail | `B01`, `L01`, `GFL` / `L42`, `L44` |
| `CODE<NN>` | far-end device code + index | `DIST01`, `ACPO03`, `CORE02` |
| `-STACK` | stack member suffix, when present | `-1`, `-2` |
| `_pFARPORT` | far-end interface; `:`/`/` → `.`, leading zeros stripped | `_P29`, `_P1.24`. If that overflows by 1, concatenate: `_P120` |

Non-numeric far ports use a bare `_` (`_LOM1`, `_X1`, `_VMNIC0`).
`UP` (access point) omits the far port entirely — an AP has one uplink, so the
port number is noise.

### 3.3 Fitting into 20 characters

A SPEED token is reserved **only when it will be emitted**, and only for the
token that will be emitted (`1G-` is 3 characters, not a worst-case `400G-`
of 5). At the class default (most fabric ports) the prefix is `USW-` / `US-`
(3–4 chars) and the ID can use the rest.

Reserving 5 characters on a 1G USW link dropped the floor on Dist→Access, so
`USW-1G-GFL-AC01_P23` (19, fits) became `USW-1G-AC01_P23`. NKN G08 has both
`GFL-ACCE01` and `L02-ACCE01`; without the floor those are the same label on
Core.

The abbreviator walks a fixed ladder and takes the **first form that fits**:

| # | Form | Example |
|---|---|---|
| 1 | `SCOPE-CODE NN-STACK _pPORT` | `GFL-AC01_P23` |
| 2 | drop stack, keep floor + dotted port | `L02-CO01_P1.1` |
| 3 | concatenate slot+port (`1.20` → `_P120`) | `L01-MG01_P120` |
| 4 | drop the far port, keep the floor | `L17-CO01-1` |
| 5 | drop the scope, keep the port | `AC01_P23` |
| 6 | code + stack only | `AC01` |

Code is always the 2-letter form (`CORE→CO` `DIST→DI` `ACCE→AC` `ACPO→AP`
`MGMT→MG` `FWGW/FWZONE→FW` …). Scope (building or far-site tail) is kept
whenever it fits — that is what tells `GFL-ACCE01` from `L02-ACCE01`. Parallel
links to the same neighbour that cannot fit floor+port collide and the script
**refuses** that device rather than aliasing two floors together.

If **no** form fits, the script **refuses** and reports the shortest form it
tried — it never emits a string EXOS would silently truncate.

### 3.4 CLASS and SPEED derivation

CLASS comes from the far-end NetBox **device role** (identity, not speed):

| Far-end role | CLASS |
|---|---|
| `Switch *` (Core / Dist / Access / Mgmt) | `USW` |
| `Firewall` | `USW` |
| `Access Point` | `UP` |
| `Sd Wan Socket` or a **circuit termination** | `UW` |
| `Server` / `Storage` / `Cohesity` data NIC | `US` |
| same roles, lights-out port (`mgmt_only`, `oob_ip` on that iface, or `idrac`/`ilo`/`bmc`) | `MON` |
| anything else at ≥ 10G | `US` |
| anything else below 10G | `MON` |
| interface carries a configured *structural* tag | `X` |

Link speed = `min(local interface type, far interface type)` from the NetBox
interface types. The SPEED token is emitted **only** when that differs from the
class default (`USW`/`US` → 10G, `UP`/`MON` → 1G). A 1G **server** NIC is
`US-1G-…`, not `MON-…`. A 1G **firewall** is `USW-1G-…`. `UW` never gets a PHY
token.

Do **not** treat “device has no primary_ip in NetBox” as management — Pure/SAN
often only have `oob_ip` recorded while the cable is a production data port.

`X` is **policy, not inference.** Stack / ISC / MLAG peer-link / SPAN ports must
never alert, but NetBox models them as ordinary switch-to-switch cables — see
the ISC ports in the sample below, which the script correctly reports as `USW`
because nothing in NetBox says otherwise. Tag those interfaces and select the
tag in **Structural (never-alert) interface tags**. Auto-`X` without a policy is
an explicit non-goal.

---

## 4. Platform CLI — what is used and why

### 4.1 EXOS

| Action | Command | Source |
|---|---|---|
| Set label | `configure ports <port_list> display-string <STRING>` | Live `show configuration` output from production switches — the switch itself emits exactly this form (`New folder (3)/scratch/probe-exos-fullcfg-20260520T203928Z/host__10_4_254_1/module__vlan.txt`) |
| Read label | `show configuration vlan` (falls back to `show configuration`) | same; the port stanza is emitted in the VLAN module |
| Clear description | `unconfig port <port_list> description-string` | doc-o-rag chunk `EXOS_User_Guide_32.7.1-314-d43e2f226a26`, *Configuring Extended Port Description* |
| Save | `save configuration` | existing runner behaviour |

> **Do not** use `show ports <list> configuration` to read labels — it truncates
> the string to 8 characters and appends `>`. Verified in
> `New folder (3)/scratch/probe-exos-10_2_30_11-*/text__show_ports_configuration_no_refresh.txt`:
> `GFL-ACPO>None       E       A   ON  ON ...`

**`description-string` must stay empty.** doc-o-rag chunk
`EXOS_User_Guide_32.7.1-471-562d1f4a10e5` (*ExtremeXOS Port Description String*):

> provides a configurable per-port “display-string” parameter that is displayed
> on each of the `show port` CLI commands, exposed through the SNMP ifAlias
> element […] This feature provides a new and separate per-port field call
> “description-string” that allows you to configure strings up to 255
> characters.
> Some characters are not permitted […] `“ < > : <space> &`. The first
> character should by alphanumeric.

`zabbix/notes/verified-facts.md` records the canary result on EXOS-VM 32.7.2.19:
when both are set, **`description-string` wins `ifAlias`**. So a port with a
`description-string` is reported as `description_string_set` — the grammar label
in `display-string` is invisible to Zabbix while that field is populated.

Length: the same file records the live truncation warning from
`CH-NKN-G08-L02-CORE01` — *"Warning: port display string exceeds maximum length
of 20 characters, truncating to …"*. The script treats that warning text as a
command rejection.

### 4.2 VOSS / Fabric Engine

| Action | Command | Source |
|---|---|---|
| Set label | `interface GigabitEthernet <slot/port>` → `name "<LABEL>"` → `exit` | Live `show running-config` from `CH-STA-L26-L02-CORE01` (PORT CONFIGURATION PHASE II blocks) |
| Read label | `show running-config` | same |
| Save | `save config` | — |

Interface-config mode form (`interface GigabitEthernet {slot/port[/sub-port]…}`)
is confirmed by doc-o-rag chunk `Fabric_Engine_9_3_User_Guide-3618-4d17c521fd18`.

`name` accepts `WORD<0-64>` and lands in **`ifAlias`** — `rcPortName` stays
empty, so do not use it (`zabbix/notes/verified-facts.md`, lab canary on Virtual
Fabric Engine 9.3.1.0). The fleet still uses the 20-character EXOS budget so one
label works on both platforms.

> **Corpus gap:** the Fabric Engine *CLI Commands Reference* is not in the
> doc-to-rag index (only the 9.3 User Guide), which is why the `name` verb is
> cited from live device configuration and the lab canary rather than from a doc
> chunk. Worth ingesting.

---

## 5. Sample compliance report

Produced by running the script's own helpers over **real NetBox topology**
(NetBox 4.5.10) and **real captured device configuration**. No credentials or
addresses are reproduced here.

> ⚠️ **Scope of this verification.** The compliance computation, both live-config
> parsers and the whole grammar path were exercised against real data. SSH was
> **not** opened from the authoring workstation (no route/credentials to the
> 10.x management network), so the transport and the remediation *push* path
> have not been executed live. Run compliance mode against one EXOS and one VOSS
> box before any remediation, and do the first push with the canary allowlist.

### 5.1 EXOS — `CH-ZRH-ZH4-CORE01` (X690-48x-2Q-4C, site CH-ZRH-ZH4)

38 live labels read · 0 description-strings · **diff 30 · orphan 8 · no_cable 34**

| ifName | Far end (NetBox) | Expected | Live | Len | Status |
|---|---|---|---|---|---|
| 1 | CH-ZRH-ZH4-CORE02::1 [Switch Core] | `USW-CORE02_p1` | `ISC` | 13 | diff |
| 5 | CH-ZRH-ZH4-MGMT01-1::1:51 [Switch Mgmt] | `USW-MGMT01-1_p1.51` | `MLAG_MGMT01_p51` | 18 | diff |
| 12 | ch-zrh-zh4-esx40…::vmnic0 [Server] | `US-ESX40_VMNIC0` | `esx40_ct1_eth0` | 15 | diff |
| 15 | CH-ZRH-ZH4-FWGW01::x1 [Firewall] | `US-FWGW01_X1` | `ZRH-FWGW01_x1` | 12 | diff |
| 20 | — | `—` | `esx45_ct1_eth0` | 0 | orphan |
| 23 | ch-zrh-zh4-san02::ct0.eth10 [Storage] | `US-SAN02_CT0.ETH10` | `SAN02_ctl0_eth10` | 18 | diff |
| 29 | ch-zrh-zh4-san01::ct0.eth10 [Storage] | `US-SAN01_CT0.ETH10` | `ZH4-SAN04-N01_CT0_e4` | 18 | diff |
| 46 | CH-ZRH-ZH5-CORE01::46 [Switch Core] | `USW-ZH5-CORE01_p46` | `ZH5-CORE01-P46` | 18 | diff |
| 48 | — | `—` | `ISP_Netrics` | 0 | orphan |

Reading it:

- Ports 1–4 and 11 are the **MLAG ISC**. NetBox models them as ordinary
  switch↔switch cables, so the script proposes `USW-…`. These are exactly the
  ports that need the structural tag → `X`.
- Port 29/30 shows a **NetBox-vs-reality disagreement**: the cable says
  `san01`, the box says `SAN04-N01`. Fix NetBox, not the switch.
- Ports 20, 21, 40, 41, 44, 47, 48 are `orphan` — labelled on the box, uncabled
  in NetBox (`ISP_Netrics`, `CATO-WAN1-Cogent`, `L50-CORE02-lag.0.2`).

### 5.2 VOSS — `CH-STA-L50-L01-CORE01` (5520-24X, site CH-STA-L50)

28 live labels read · **diff 16 · orphan 12**

| ifName | Far end (NetBox) | Expected | Live | Len | Status |
|---|---|---|---|---|---|
| 1/2 | CH-STA-L50-FWZone01::x1 [Firewall] | `US-FWZONE01_X1` | `S-FWZONE:X1` | 14 | diff |
| 1/4 | CH-STA-L50-FWZone01::ha [Firewall] | `MON-FWZONE01_HA` | `OLD_CORE50` | 15 | diff |
| 1/7 | CH-STA-L50-L01-MGMT01::1/29 [Switch Mgmt] | `USW-L01-MGMT01_p1.29` | `NNI:L50-L01-MGMT01_1/29` | 20 | diff |
| 1/10 | CH-STA-P-BACK02::LOM1 [Server] | `US-P-BACK02_LOM1` | `Backup_SRV_LAN1` | 16 | diff |
| 1/17 | CH-STA-L50-B01-DIST01::29 [Switch Dist] | `USW-B01-DIST01_p29` | `L50-B01-Di01:29` | 18 | diff |
| 1/20 | CH-STA-L50-L01-DIST01::29 [Switch Dist] | `USW-L01-DIST01_p29` | `L50-L02-Di02:54` | 18 | diff |
| 1/21 | CH-STA-L50-L02-DIST01::54 [Switch Dist] | `USW-L02-DIST01_p54` | `L50-L01-Di01:29` | 18 | diff |
| 1/22 | CH-STA-L42-CORE01-2::2:14 [Switch Core] | `USW-L42-CO01-2_p2.14` | `L42-Co01:1:14` | 20 | diff |
| 1/24 | CH-STA-L50-L01-CORE02::1/24 [Switch Core] | `USW-L01-CORE02_p1.24` | `NNI:L50-Co02:1/24` | 20 | diff |
| 2/2 | CH-STA-L26-L02-CORE01::2/2 [Switch Core] | `USW-L26-CORE01_p2.2` | `NNI:L26-Co01:2/2` | 19 | diff |

Reading it:

- Every live VOSS label containing `:` (`S-FWZONE:X1`, `NNI:L26-Co01:2/2`) is
  legal on VOSS but **forbidden by the fleet grammar** and would be rejected by
  EXOS — one reason to normalise both platforms onto the same generator.
- `1/7` live label is **23 characters** — fine on VOSS (`WORD<0-64>`), but it
  would be truncated to 20 on EXOS. The generated form is exactly 20.
- `1/20` / `1/21` are **swapped** between the on-box labels and the NetBox
  cabling — precisely the class of error this script exists to surface.
- `1/4` is the firewall HA link at 1G, so the current generator emits `USW-1G-…`
  (firewall is `USW`; token because the class default is 10G), not `MON-…`.
- Longest generated label across both devices is **20** — at budget, never over.

### 5.3 What the sample proves

- SPEED is omitted throughout because every link runs at its class default.
- The cross-site uplink `1/22` needed tier 2 of the ladder
  (`USW-L42-CORE01-2_p2.14` = 22 → `USW-L42-CO01-2_p2.14` = 20).
- Nothing longer than 20 was ever emitted.

The **Expected** column in the tables above was produced by an earlier generator
that reserved a SPEED slot on every port and classified firewalls as `US`. Do
not treat those strings as the current golden output — re-run compliance.

---

## 6. Remediation

Double-gated: `mode=remediate` **and** *Commit changes*. With `remediate` but no
commit, the script prints the exact command block per device and stops.

Per port it pushes only what is non-compliant:

```
# EXOS
configure ports 1:8 display-string USW-L02-ACCE03_p23
unconfigure port 1:8 description-string      # only if explicitly ticked

# VOSS
interface GigabitEthernet 1/17
name "USW-B01-DIST01_p29"
exit
```

then `save configuration` / `save config` once per device.

Safety properties:

- refuses any label > 20 characters or containing a forbidden character,
  immediately before the write, not only at generation time;
- treats the EXOS truncation warning **and VOSS CLI errors** as a rejection and
  aborts that device before `save`, so a half-applied device is never written to
  flash;
- does **not** clear EXOS `description-string` unless that box is ticked;
- prefers `oob_ip` for SSH;
- idempotent — a port already at the expected label produces no command;
- the canary allowlist restricts the push to named `device::ifname` pairs.

---

## 7. Non-goals (v1)

Zabbix template edits · renaming NetBox devices · replacing Golden Config ·
auto-`X` on every unused port without a policy · LAG / MLAG / MLT label grammar
(still TBD upstream in `port-identity-foundation.md` §6).
