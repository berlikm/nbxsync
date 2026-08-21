# Extreme Port Mute — NetBox custom script

`extreme_port_mute.py` admin-disables or admin-enables a port, or prefixes the live on-box
label with `X-`, from a **required allowlist**. It is **not** a mode on
[Extreme Port Labels](README-extreme-port-labels.md): cabling remediate must
never be able to shut (or unshut) an uplink.

Platform is detected from the NetBox device (`EXOS` / Switch Engine vs
`VOSS` / Fabric Engine). EXOS stacks SSH via the member that holds
`oob_ip` / `primary_ip` (the VC master) — `configure` / `disable` / `enable` for slot 2
still run on that login.

## Install

Same directory as the labels script:

```
/opt/netbox/netbox/scripts/
├── extreme_cli_runner.py
├── extreme_firmware_upgrade.py
├── extreme_port_labels.py      # required sibling — mute loads it by path
└── extreme_port_mute.py
```

Copy **both** `extreme_port_labels.py` and `extreme_port_mute.py`. Mute does
not replace labels. Not HostSync, not zerotouch, not
`configure_nbxsync_network.py --apply`.

Same credentials as labels (`NBX_NAPALM_EXOS_*` / `NBX_NAPALM_VOSS_*`,
`EXTREME_VENV_PATH`).

Unit tests:

```bash
python3 zabbix/notes/test_extreme_port_mute.py
```

## What to paste

Full NetBox hostname, one port per line. No ranges.

```
NL-ENS-NEP-GFL-CORE01-1::2:10
NL-ENS-NEP-GFL-CORE01-1::2:11
NL-ENS-NEP-GFL-CORE01-1::2:12
NL-ENS-NEP-GFL-CORE01-1::2:13
NL-ENS-NEP-GFL-CORE01-1::2:14
NL-ENS-NEP-GFL-CORE01-1::2:15
NL-ENS-NEP-GFL-CORE01-1::2:16
NL-ENS-NEP-GFL-CORE01-1::2:17
```

`2:10` and `2/10` match. `#` comments are allowed. On this estate those
GFL `2:10`–`2:17` rows are unused slot-2 data ports (no complete cable).
SummitStack on that pair is `1:27`/`1:28` and `2:27`/`2:28` — the script
refuses `extreme-summitstack` even if they appear in the paste.

## Actions

| Action | EXOS | VOSS | When |
|---|---|---|---|
| **shutdown** (default) | `disable port 2:10` | `interface GigabitEthernet 2/10` then `shutdown` | Unused Core/Dist/Mgmt: admin-down |
| **no_shutdown** | `enable port 2:10` | `interface GigabitEthernet 2/10` then `no shutdown` | Bring an admin-down port back up |
| **x_prefix** | `configure ports 2:10 display-string X-…` and `unconfigure port 2:10 description-string` | `name "X-…"` under GigabitEthernet | Keep the link up; Zabbix IFALIAS mute |

`X-` keeps the live display-string (or `name`), prefixes `X-`, and cuts from
the **end** at 20 characters (EXOS `display-string` max). Empty live → `X`.
Already `X` / `X-…` is not double-prefixed. Do **not** put `X-` in EXOS
`description-string` — that field wins `ifAlias` and hides the display-string.

## Safety

- Allowlist required. No “entire scope”.
- Preview = NetBox only. Apply without Commit = SSH, print commands. Apply +
  **Commit changes** = push.
- SummitStack / stacking ports always skipped.
- Complete NetBox cables skipped unless **Allow cabled ports** is ticked.
  Cables tagged `nbx-ingestor: Orphaned` do **not** count as cabled (the
  ingestor marked them gone; NetBox deletes them after ~30 days).
- Per-port commands only (no `2:10-2:17` ranges) so the transcript is 1:1.
- EXOS stacks: one SSH login to the master; `CORE01-1::2:10` is valid.
- Does **not** write NetBox `Interface.enabled`. Admin-down / admin-up there
  separately if you want NetBox to match the box.
- Save config defaults on (`save configuration` / `save config`), same as labels.

## Modes

1. **Preview** — resolve names, platform, cables, stack-port refusal. No SSH.
   Shutdown and no-shutdown already show the CLI. `X-` waits for a live read.
2. **Apply** without Commit — SSH, read live labels, show commands.
3. **Apply** + Commit — push, then save.

CSV is in the job Output tab.
