# Extreme Port Labels — NetBox custom script

`extreme_port_labels.py` computes the expected on-box port label
`CLASS[-SPEED]-ID` from **NetBox cabling**, reads the **live** label off each
Extreme switch, and reports the diff. Optionally it remediates.

The label lands in SNMP `ifAlias`, which is what Zabbix LLD filters on
(`{$NET.IF.IFALIAS.MATCHES}`). A wrong or truncated label silently drops a port
out of — or into — monitoring.

Grammar authority: [`../reference/port-identity-foundation.md`](../reference/port-identity-foundation.md),
[`verified-facts.md`](verified-facts.md).
This README only adds what those documents leave open: **how the ID is derived
from NetBox topology**, **which CLI verbs are used**, and **how to read a
compliance job**.

---

## 1. Install

NetBox loads every `.py` in `SCRIPTS_ROOT` as a script module, so this is a
single flat file next to the others. On this estate that directory is
`/opt/netbox/netbox/scripts/`:

```
/opt/netbox/netbox/scripts/
├── extreme_cli_runner.py       # SSH transport — reused, not forked
├── extreme_firmware_upgrade.py
└── extreme_port_labels.py      # this script
```

It reuses the CLI runner's session helpers and credential resolution by loading
the runner **by file path** (`importlib`), because NetBox loads each script
module in isolation and a plain `import extreme_cli_runner` is not reliable.

The loader searches, in order: the directory of this file, `…/scripts/` under
that directory and its parent, Django `SCRIPTS_ROOT` / `BASE_DIR`. That covers
both “both files in `scripts/`” and an older copy sitting at
`/opt/netbox/netbox/` while the runner stayed in `scripts/`. A compatibility
symlink `BASE_DIR/extreme_cli_runner.py → scripts/extreme_cli_runner.py` is
optional once this search is deployed.

The loaded module is registered in `sys.modules` **before** `exec_module`.
Python 3.12 dataclasses look up `cls.__module__` there; skipping that
registration fails even when the path is correct.

If the runner cannot be loaded the job log prints `runner_loaded False` and
compliance/remediate refuse to open SSH. Preview still runs (cabling only).

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
python3 zabbix/notes/export_port_label_preview.py   # regenerates the Excel sheet + summary
```

What the current generator will write (1535 cabled ports):
[`port-label-preview.md`](port-label-preview.md) (eyeball sheet),
[`port-label-verify.md`](port-label-verify.md) (every port, grouped by switch),
[`fixtures/port_label_preview.tsv`](fixtures/port_label_preview.tsv) (Excel).

How to run this in NetBox (preview → Excel → compliance → one canary push):
[`port-label-compliance-review.md`](port-label-compliance-review.md).

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
| **Mode** | `preview` (default, **no SSH**) · `compliance` (read the box) · `remediate` (push; needs Commit) |
| **Commit changes** | NetBox's own box. Remediation needs **both** mode=remediate and this |
| **Scope** | site group / site / role / device tag / explicit devices — **this** is what preview uses. Every filter is **AND** (picking devices no longer ignores site or platform) |
| **Platform (EXOS / VOSS)** | `VOSS only` never includes EXOS, even with a device list or site. Same for EXOS only. Applied with site / role / tag / site group |
| **Platforms (device list)** | Optional NetBox platform objects. The Devices dropdown follows this (`platform_id`). Pick Fabric Engine / VOSS here so the picker is VOSS-only |
| **Canary allowlist** | **Remediate only**, ignored in preview/compliance. `device-name::ifname` per line; `1:17` and `1/17` match. Required to push unless "entire scope" is ticked |
| **Remediate entire scope** | Off by default. Ignored unless Mode is Remediate |
| **Structural tags** | interface tags meaning "never alert" (SPAN / mute) → expected label `X`. Do **not** tag stack / ISC / MLAG peer |
| **Include admin-down / X·N** | reporting breadth |
| **Also clear EXOS description-string** | off by default (may hold human text). SSH / remediate |
| **Fail the job on blocking label diffs** | scheduled compliance. Unreachable boxes **always** fail the job |
| **Concurrent workers** | Parallel **logins** (one session per switch). All ports on a box share that session |

**Scope rule:** cabled ports get an expected grammar label from NetBox topology.
A port with **no complete cable path** cannot derive a far end — it is **not**
pushed. If the box still has a live label or EXOS `description-string`, that
text is **kept** and listed in compliance as `kept` (it often still means
something: ISP, leftover NIC). We do not blank the box to look tidy.

SSH uses **`oob_ip` first**, then `primary_ip`. Site groups include **nested children**.
Compliance and remediate open **one SSH login per switch**: `show configuration vlan`
(or VOSS `show running-config`) once, then every port on that box is compared in
memory. Remediate with **Commit** pushes on **that same session**, then disconnects.
Workers are concurrent *devices*, not concurrent ports. Duplicate NetBox names /
pks are skipped so EXOS is not hammered with a second login.

If login fails, every port on that switch is `status=unreachable` with the **same
short** `detail` (`SSH session failed (1 login, N port(s)): …`). That is one
failed session copied onto the CSV, not N separate connections. The job log
prints the full netmiko blob **once**.

Per-port statuses:

| Status | Meaning | Blocking? | Rewritten on remediate? |
|---|---|---|---|
| `planned` | **Preview only.** Cabling produced a label. Box was not read. | no | unknown (no SSH) |
| `ok` | **Compliance.** Zabbix ifAlias **already is** the expected grammar | no | no |
| `diff` | live display-string / VOSS `name` ≠ expected | yes | **yes** |
| `missing` | cabled in NetBox, no live label | yes | **yes** |
| `too_long` | no ID form fits 20 characters (shortest form is still in `expected`) | yes | no (refused) |
| `forbidden` | live label or ifName has a character EXOS would treat as a second command | yes | yes if expected is safe |
| `alias_hijacked` | EXOS display-string matches, but `description-string` still wins ifAlias | yes | only if “clear description-string” is ticked |
| `unreachable` | no SSH (missing IP or session failed) | yes | no |
| `kept` | live label, no complete cable — listed, never wiped | no | **never** |
| `applied` | remediator wrote this port | no | already done |

`collision=yes` on the CSV is also blocking: two ports on the **same switch**
share an expected grammar label. Policy labels `X` / `N` are excluded (every
SPAN port is supposed to be `X`). The generator still emits both colliding
rows (it cannot know which cable is wrong); the job must not look clean.

Preview has no SSH, so `live` / `description_string` / `rewrite` are empty and
every derived row is `status=planned` — that is **not** “already on the box”.
CSV `netbox_description` is the current NetBox interface description (what is
on the port today). `speed_source` is `iftype:<slug>` or `speed:<kbps>kbps`
from the slower of local/far — empty when neither NetBox field has a rate
(`extreme-summitstack`).

**Compliance** fills `live` and `rewrite`. Filter `rewrite=yes` for the
overwrite queue (`diff` / `missing` / `forbidden`). `ok` means leave it.
The job log also has a **Would rewrite on next remediate** table (capped at
40; the CSV is the full list).

How to read a job: log is the **scorecard** (truncated tables). CSV in the
**Output** tab is the archive. Details:
[`port-label-compliance-review.md`](port-label-compliance-review.md).

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
ID = [<SCOPE>-]<CODE><NN>[-<STACK>][_FARPORT]
```

| Piece | Source | Example |
|---|---|---|
| `SCOPE` | a token that exists on the **hostname** (or was stripped from it) — never a NetBox site tail like `DC` that is not in the name | `B01`, `L01`, `GFL`, `L50` |
| `CODE<NN>` | **Fabric** (switch/firewall/AP): short codes (`CORE→C`, `DIST→D`, `ACCE→A`, `MGMT→M`; unknown `SPINE→SP`). **Endpoints**: the hostname word (`SAN`, `SNAS`, `ESX`) | `D01`, `A03`, `SAN11`, `SNAS01` |
| `-STACK` | hostname `-1`/`-2`, **only when the far port does not already start with that member** | omitted on `2:10` (the slot *is* the member → `_2_10`); kept on unslotted `48` → `-2_48` |
| `_FARPORT` | far-end interface; `:`/`/`/`.` → `_`, leading zeros stripped | `_29`, `_1_24`. If that overflows, concatenate: `_120`. No extra `P`. Filler `ETH`/`NIC`/`PORT` drops (`ct0.eth4` → `_CT0_4`). ESXi `vmnic1` → `_NIC1`. Lights-out `MGMT` → `_MG`. |

Non-numeric far ports use a bare `_` (`_LOM1`, `_X1`, `_NIC0`).
`UP` (access point) omits the far port entirely — an AP has one uplink, so the
port number is noise.

### 3.3 Fitting into 20 characters

A SPEED token is reserved **only for the token that will actually be emitted**
(`1G-` is 3, `40G-` is 4). We do **not** leave a blank 5-character `400G-` hole
on a 1G link — that is what dropped floors. Room for `40G` / `100G` comes from
**short fabric codes** (`CORE→C` `DIST→D` `ACCE→A` `MGMT→M`) **and** dropping the extra `P` on ports
(`_1_20` not `_P1_20`). `USW-40G-L01-M01_1_20` is 20; spelling CORE or keeping
`P` would overflow. CLASS tokens stay `USW`/`UP`/`US` — renaming them to
`SW`/`AP`/`S` would miss live Access LLD (`USW|US|UP|MON|UW|TMON`) until
the role macros are rewritten.
Endpoint names stay readable (`SAN`, `SNAS`, `ESX`) — we
do not invent `SN`/`NS`/`CY`/`DC`.

Reserving 5 characters on a 1G USW link dropped the floor on Dist→Access, so
`USW-1G-GFL-A01_23` (17, fits) became `USW-1G-A01_23`. NKN G08 has both
`GFL-ACCE01` and `L02-ACCE01`; without the floor those are the same label on
Core.

The abbreviator walks a fixed ladder and takes the **first form that fits**:

| # | Form | Example |
|---|---|---|
| 1 | `SCOPE-CODE-STACK _PORT` | `GFL-A01_23` |
| 2 | slotted stack: drop hostname `-1`/`-2`, keep floor + `_member_port` | `L02-C01_2_16` |
| 3 | concatenate slot+port (`1_20` → `_120`) | `L01-M01_120` |
| 4 | drop the far port, keep the floor | `L17-C01-1` |
| 5 | drop the scope, keep the port | `A01_23` |
| 6 | code + stack only | `A01` |

**Fabric** codes: `CORE→C` `DIST→D` `ACCE→A` `ACPO→AP`
`MGMT→M` `FWGW/FWZONE→FW`, unknown `SPINE→SP`. A slotted stack uplink
is `USW-1G-L02-C01_1_1` — the member is `_1_1`, not a second `-1`.
**Do not drop the far port** on stack links (`1:15` vs `1:16` must stay
distinct). Hostname `-2` remains only when the ifName is unslotted.
**Endpoints keep the hostname
word** (`SAN`, `SNAS`, `ESX`) and only shorten that word if 20 characters force
it. Scope (building or a site token that is actually on the hostname) is kept
whenever it fits — that is what tells `GFL-ACCE01` from `L02-ACCE01`.

If two ports on the **same switch** still share an expected label after the
ladder, preview/compliance set `collision=yes` and the row is **blocking**. The
script does not pick a winner. If **no** form fits 20 characters, status is
`too_long` and `expected` holds the shortest form tried — it never emits a
string EXOS would silently truncate.

### 3.4 CLASS and SPEED derivation

CLASS comes from the far-end NetBox **device role** (identity, not speed):

| Far-end role | CLASS |
|---|---|
| `Switch *` (Core / Dist / Access / Mgmt) | `USW` |
| `Firewall` | `USW` |
| `Access Point` | `UP` |
| `Sd Wan Socket` or a **circuit termination** | `UW` |
| `Server` / `Storage` / `Cohesity` / `ESXi Hypervisor` data NIC | `US` |
| same roles, lights-out port (`mgmt_only`, `oob_ip` on that iface, `idrac`/`ilo`/`bmc`, or Cohesity `NIC.Embedded`) | `MON` |
| **anything else** (printer, camera, generic “Network Device”, …) | `MON` |
| interface carries a configured *structural* tag | `X` |

Link speed = `min(local, far)` from NetBox **interface type first**
(`10gbase-x-sfpp` → 10000 Mbps), falling back to `Interface.speed` **in Kbps**
(`/1000`). Preview CSV `speed_source` says which field won
(`local:iftype:1000base-t`, `far:speed:10000000kbps`, or empty).
`extreme-summitstack` has no PHY rate — SPEED is omitted (stack rows look
`ok` with an empty speed). The SPEED token is emitted **only** when that
differs from the class default (`USW`/`US` → 10G, `UP`/`MON` → 1G). A 1G
**server** NIC is `US-1G-…`, not `MON-…`. A 1G **firewall** is `USW-1G-…`.
`UW` never gets a PHY token. Do **not** invent 10G when NetBox says 1G —
`US-1G-SAN10-N01` keeps the `1G` token because US defaults to 10G; fixing
the iftype in NetBox is what drops it.

Do **not** treat “device has no primary_ip in NetBox” as management — Pure/SAN
often only have `oob_ip` recorded while the cable is a production data port.
Cohesity **iLO** is the dedicated LOM named
`Embedded NIC … (NIC.Embedded.1-1)` (and/or a local description `COH-N01-ILO`).
That is `MON-SAN10-N01`, not `US-1G-…`. The lab-room hostname prefix `LR50`
is omitted so 10G still fits (`MON-10G-SAN10-N13`). A Cohesity **data** NIC
stays `US`. The description is a CLASS hint only — ID still comes from the
far hostname (`n08` on the cable, even if the description says `N07`).
Dell iDRAC ifNames render as `ILO` in the port token (`iDRAC 10` → `_ILO10`);
CLASS still matches the raw ifName (`idrac` in `BMC_PORT_TOKENS`).
ESXi `vmnic1` is `_NIC1` (not `_VMNIC1`). A SAN/firewall `MGMT` port is `_MG`,
so `CTE0.B.MGMT` is `MON-SAN01_CTE0_B_MG` at 1G and `MON-10G-SAN01_B_MG`
when SPEED is needed — not the concatenated `CTE0BMGMT`.

`X` is **policy, not inference.** Use it for SPAN / lab / operator mute. **Stack,
ISC, and MLAG peer-links are ordinary switch↔switch cables** — the script
correctly labels them `USW` and they **must stay monitored** (split-stack /
dual-active is an outage). Do not tag them structural. Auto-`X` from a
description of `ISC` is an explicit non-goal.

### 3.5 What is closed vs open (so this script is not a catalogue)

The generator is two layers. Mixing them is how `CY` / `NS` / `DC` appeared:
someone encoded *this estate’s inventory* instead of *the grammar*.

**Open — follows NetBox, no per-device rows**

| Mechanic | What happens when you add a new box |
|---|---|
| Hostname ID | Keep the words on the name (`SAN`, `SNAS`, `ESX`, `SAN10-N01`). Shorten the prefix only if 20 characters force it. |
| Site strip | Token-wise shared prefix with the far-site slug. Never invent a site tail (`DC`) that is not on the hostname. |
| Port token | Split on `:` `/` `.`; drop generic filler (`ETH`, `NIC`, `PORT`); no extra `P`. Dell `iDRAC` → `ILO`, ESXi `vmnic` → `NIC`, `MGMT` → `MG`. |
| Length | Longest ID that fits the *emitted* SPEED token. Refuse rather than truncate. |
| Unknown CLASS | Anything that is not switch/firewall/AP/SD-WAN/server/storage/cohesity/hypervisor is `MON`. |
| SPEED token | `Mbps → NG` / `2G5`. 50G / 200G / 800G do not need a table row. |
| New USW role-word | `Switch Spine` / hostname `SPINE01` → `SP` (two letters, same physics as `CORE→C`). |

**Closed — a small policy table, edited when the *taxonomy* changes**

| Table | When you touch it |
|---|---|
| `INFRA_ROLE_TOKENS` / `DATA_ENDPOINT_ROLE_TOKENS` | You invent a NetBox role instead of reusing Server / Storage / Switch \*. Prefer **not** inventing roles. |
| `BMC_PORT_TOKENS` | A new lights-out vendor string, and nobody set `oob_ip` / `mgmt_only`. Cohesity iLO is `NIC.Embedded` (not a global LOM token). |
| `FABRIC_CODE_SHORT` | Estate spelling that is *not* “first two letters” (`FWZONE→FW` not `FZ`, `CATO→CT` not `CA`). |
| `_PORT_NOISE` | A new filler word in vendor ifNames (`QSFP`, `SLOT`) that burns the 40G budget. |

Operational contract that keeps the script stable: **reuse NetBox roles**. A
NAS is Storage. A new leaf switch is still Switch \*. `ESXi Hypervisor` is
treated as a data-path role (`US` on vmnic, `MON` on iDRAC). Inventing
“HCI” / “Tape” without adding a token still labels those NICs `MON`.

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

**Existing `description-string` is kept.** It may be human text. The script
lists every non-empty one in compliance and **does not clear it** unless that
box is ticked. While it is set it still **wins `ifAlias`** (lab canary on
EXOS-VM 32.7.2.19), so Zabbix sees that text rather than the grammar in
`display-string` — that is why it is listed, not because we want to delete it.

Length: live truncation warning from `CH-NKN-G08-L02-CORE01` — *"Warning: port
display string exceeds maximum length of 20 characters, truncating to …"*. The
script treats that warning text as a command rejection.

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

## 5. Operations report (what NetBox can actually give you)

A Custom Script is not a dashboard. The best report we can ship without a
plugin is:

1. **Job log** — counts, CLASS mix, **per-device scorecard**, then at most 40
   blocking / kept rows. NetBox truncates one huge markdown table, so a
   fleet-wide scorecard is split into log entries of 200 switches (`1/2`,
   `2/2`) — that is the same table, not a second run. Do not treat the log
   as the archive.
2. **Output tab CSV** — every evaluated port. Copy into Excel. First line is
   `sep=,` plus a UTF-8 BOM so Excel keeps commas and encoding. VOSS `1/17` is
   written as a text formula so Excel does not turn it into a date.
3. **Job colour** — success only when nothing blocking remains. Unreachable
   boxes **always** fail the job (`log_failure`, clickable device). Tick **Fail
   the job on blocking label diffs** on a schedule so leftover `diff` rows also
   go red. A first interactive fleet run will be almost all `diff`; leave that
   tick off then.

`ok` means **Zabbix will see the expected grammar on ifAlias**. It does **not**
mean “display-string matches.” On EXOS, `description-string` still wins
ifAlias. That row is `alias_hijacked` (blocking) until you tick clear.
Preview uses `planned` instead of `ok` so a cabling-only run cannot look
like the fleet already matches.

CSV columns worth filtering:

| Column | Filter |
|---|---|
| `rewrite=yes` | **Overwrite queue.** What remediate would push. Empty in preview. |
| `blocking=yes` | Work queue. Includes unreachable and hijacked, not `kept`. |
| `status=planned` | Preview: label derived, box not read |
| `status=diff` | Box label ≠ cabling |
| `status=missing` | Cabled, no live label |
| `status=alias_hijacked` | Grammar is on display-string; Zabbix still reads description-string |
| `status=unreachable` | No SSH — the job must not go green |
| `status=kept` | Live label, no cable. Listed, never wiped |
| `collision=yes` | Two ports on this switch share `expected` |
| `class` | `USW` / `US` / `UP` / `MON` / `UW` / `X` |
| `ifalias_source` | `display-string` · `description-string` · `name` |
| `len=20` | At the EXOS budget; check it still reads |

Runbook (preview → Excel → one EXOS + one VOSS compliance → canary push):
[`port-label-compliance-review.md`](port-label-compliance-review.md).

---

## 6. Sample: live box vs current generator

Produced by running the script's own helpers over **real NetBox topology**
(NetBox 4.5.10) and **real captured device configuration**. No credentials or
addresses are reproduced here. Expected values are what **this** generator
emits (hostname identity, no extra `P`, SPEED only when not the class default).

> ⚠️ **Scope of this verification.** The compliance computation, both live-config
> parsers and the whole grammar path were exercised against real data. SSH was
> **not** opened from the authoring workstation (no route/credentials to the
> 10.x management network), so the transport and the remediation *push* path
> have not been executed live. Run compliance mode against one EXOS and one VOSS
> box before any remediation, and do the first push with the canary allowlist.

### 6.1 EXOS — `CH-ZRH-ZH4-CORE01` (X690-48x-2Q-4C, site CH-ZRH-ZH4)

38 live labels read · 0 description-strings · **diff 30 · kept 8**

| ifName | Far end (NetBox) | Expected | Live | Len | Status |
|---|---|---|---|---|---|
| 1 | CH-ZRH-ZH4-CORE02::1 [Switch Core] | `USW-C02_1` | `ISC` | 9 | diff |
| 5 | CH-ZRH-ZH4-MGMT01-1::1:51 [Switch Mgmt] | `USW-M01_1_51` | `MLAG_MGMT01_p51` | 12 | diff |
| 12 | ch-zrh-zh4-esx40…::vmnic0 [Server] | `US-ESX40_NIC0` | `esx40_ct1_eth0` | 13 | diff |
| 15 | CH-ZRH-ZH4-FWGW01::x1 [Firewall] | `USW-FW01_X1` | `ZRH-FWGW01_x1` | 11 | diff |
| 20 | — | `—` | `esx45_ct1_eth0` | — | kept |
| 23 | ch-zrh-zh4-san02::ct0.eth10 [Storage] | `US-SAN02_CT0_10` | `SAN02_ctl0_eth10` | 15 | diff |
| 29 | ch-zrh-zh4-san01::ct0.eth10 [Storage] | `US-SAN01_CT0_10` | `ZH4-SAN04-N01_CT0_e4` | 15 | diff |
| 46 | CH-ZRH-ZH5-CORE01::46 [Switch Core] | `USW-ZH5-C01_46` | `ZH5-CORE01-P46` | 14 | diff |
| 48 | — | `—` | `ISP_Netrics` | — | kept |

Reading it:

- Ports 1–4 and 11 are the **MLAG ISC**. NetBox models them as ordinary
  switch↔switch cables, so the script proposes `USW-…`. **Keep that** — ISC
  must alert. Do not tag them `X`.
- Port 29/30 shows a **NetBox-vs-reality disagreement**: the cable says
  `san01`, the box says `SAN04-N01`. Fix NetBox, not the switch.
- Ports 20, 21, 40, 41, 44, 47, 48 have a live label and **no cable** in
  NetBox (`ISP_Netrics`, leftover NICs). Status is **`kept`**: we list them,
  we do not blank the box.

### 6.2 VOSS — `CH-STA-L50-L01-CORE01` (5520-24X, site CH-STA-L50)

28 live labels read · **diff 16 · kept 12**

| ifName | Far end (NetBox) | Expected | Live | Len | Status |
|---|---|---|---|---|---|
| 1/2 | CH-STA-L50-FWZone01::x1 [Firewall] | `USW-FW01_X1` | `S-FWZONE:X1` | 11 | diff |
| 1/4 | CH-STA-L50-FWZone01::ha [Firewall] | `USW-1G-FW01_HA` | `FWZONE-HA1` | 14 | diff |
| 1/7 | CH-STA-L50-L01-MGMT01::1/29 [Switch Mgmt] | `USW-L01-M01_1_29` | `NNI:L50-L01-MGMT01_1/29` | 16 | diff |
| 1/17 | CH-STA-L50-B01-DIST01::29 [Switch Dist] | `USW-B01-D01_29` | `L50-B01-Di01:29` | 14 | diff |
| 1/20 | CH-STA-L50-L01-DIST01::29 [Switch Dist] | `USW-L01-D01_29` | `L50-L02-Di02:54` | 14 | diff |
| 1/21 | CH-STA-L50-L02-DIST01::54 [Switch Dist] | `USW-L02-D01_54` | `L50-L01-Di01:29` | 14 | diff |
| 1/22 | CH-STA-L42-CORE01-2::2:14 [Switch Core] | `USW-L42-C01_2_14` | `L42-Co01:1:14` | 16 | diff |
| 1/24 | CH-STA-L50-L01-CORE02::1/24 [Switch Core] | `USW-L01-C02_1_24` | `NNI:L50-Co02:1/24` | 16 | diff |
| 2/2 | CH-STA-L26-L02-CORE01::2/2 [Switch Core] | `USW-L26-C01_2_2` | `NNI:L26-Co01:2/2` | 15 | diff |

Reading it:

- Every live VOSS label containing `:` (`S-FWZONE:X1`, `NNI:L26-Co01:2/2`) is
  legal on VOSS but **forbidden by the fleet grammar** and would be rejected by
  EXOS — one reason to normalise both platforms onto the same generator.
- `1/7` live label is **23 characters** — fine on VOSS (`WORD<0-64>`), but EXOS
  would truncate it. The generated form `USW-L01-M01_1_29` is 16 (`M` not
  `MGMT`; `_` not `.`; no extra `P`).
- `1/20` / `1/21` are **swapped** between the on-box labels and the NetBox
  cabling — precisely the class of error this script exists to surface.
- `1/4` is the firewall HA link at 1G, so the generator emits `USW-1G-FW01_HA`
  (firewall is `USW`; SPEED because the class default is 10G), not `MON-…`.
- Longest generated label across both devices is **20** — at budget, never over.

### 6.3 What the sample proves

- SPEED is omitted at the class default. The 1G firewall HA is the exception
  (`USW-1G-FW01_HA`) because `USW` defaults to 10G.
- Cross-site `1/22` is `USW-L42-C01_2_14` (16). The stack member is the
  slotted port (`2_14`), not a second `-2` on the hostname. Spelling `CORE`
  would overflow.
  Fabric codes stay `C`/`D`/`A`/`M`. 40G on a slotted mgmt uplink is
  `USW-40G-L01-M01_1_20` (20) — that only fits because there is no extra `P`.
- Dots are forbidden. Slot/port uses `_` (`_2_14`, never `_p2.14`).
- Live on-box strings (`L02-ACCE03_p23`, `L42-Co01:1:14`) stay in the Live
  column. Compliance lists them; it does not wipe them to look tidy.
- Endpoint IDs keep hostname words: Cohesity `lr50-san10-n08` →
  `MON-SAN10-N08` (not `CY08`, not `LR50-…`). `SNAS01` stays `SNAS`, `san11`
  stays `SAN`. A NetBox site slug that is not on the hostname (`ch-zrh-dc`)
  is not invented as `DC`. Dell iDRAC is `_ILO10`, not `_IDRAC10`. ESXi
  `vmnic` is `_NIC3`. `MGMT` is `_MG`.

---

## 7. Remediation

Double-gated: `mode=remediate` **and** *Commit changes*. With `remediate` but no
commit, the script prints the exact command block per device and stops.

With Commit, the write uses the **same SSH session** that just read live labels
(no second login). Per port it pushes only what is non-compliant:

```
# EXOS
configure ports 1:8 display-string USW-1G-L02-A03_23
unconfigure port 1:8 description-string      # only if explicitly ticked

# VOSS
interface GigabitEthernet 1/17
name "USW-B01-D01_29"
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

## 8. Non-goals (v1)

Zabbix template edits · renaming NetBox devices · replacing Golden Config ·
auto-`X` on stack / ISC / MLAG peer (those are `USW`) · LAG / MLAG / MLT bundle
label grammar (still TBD upstream in `port-identity-foundation.md` §6).
