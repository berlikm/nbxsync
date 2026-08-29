# Verified facts

Things we confirmed, with the source. Do not re-litigate these without new evidence.

## EXOS

| Fact | Value | Source |
|---|---|---|
| `display-string` max | **20 chars, silently truncated** | live switch CH-NKN-G08-L02-CORE01: *"Warning: port display string exceeds maximum length of 20 characters, truncating to ..."* |
| `description-string` max | 255 chars | EXOS UG 32.7.1 |
| SNMP `ifAlias` visible size | 64 default, 255 with `config snmp ifmib ifalias size extended` | EXOS UG 32.7.1 |
| `ifAlias` is the exposed object | yes, IfXTable / IF-MIB RFC 2233 | EXOS UG 32.7.1 |
| **`ifAlias` precedence** | `description-string` **wins** when both are set (either order); either alone is used | canary, EXOS-VM 32.7.2.19 |
| Forbidden chars in `description-string` | `"` `<` `>` `:` `?` `&` space; first char alphanumeric | EXOS UG 32.7.1 (union of two sections) |
| "15 character limit" | never existed — legacy plant convention | — |

**Decision:** grammar goes in `display-string` (visible in everyday `show ports`), `description-string` stays **empty**. The two cannot be combined — `description-string` always hijacks `ifAlias`.

**Consequence:** fleet label budget is **20 characters**, not 64. Worst-case prefix `USW-100M-` = 9, leaving 11 for the ID. IDs must be machine-short abbreviations; full identity lives in NetBox.

## VOSS

Lab: Virtual Fabric Engine 9.3.1.0 (5520-24T-FabricEngine), Zabbix 7.0.29 — [templates/extreme_voss_snmp/LAB_RESULTS.md](../templates/extreme_voss_snmp/LAB_RESULTS.md)

| Fact | Value | Source |
|---|---|---|
| Port `name` max | **0–64 chars** (`WORD<0-64>`) | live CLI on CH-STA-L50-L01-CORE01 |
| **`name` → `ifAlias`** | **YES** — `name USW-ID01` → `ifAlias.192 = "USW-ID01"` | lab canary |
| `rcPortName` | **empty even when `name` is set** — do not use | lab canary |
| CPU | `rcKhiSlotCpuCurrentUtil.<slot>` | lab |
| Memory | `rcKhiSlot*` used / free / util | lab |
| `rcSysCpuUtil`, `rcSysDramSize/Used/Free` | **No Such Object** — do not use | lab |
| `hrSystemUptime.0` | **No Such Object** — `sysUpTime.0` only | lab |
| Temperature | 7-sensor LLD, **reads 0 °C on the VM** | lab |
| PSU | `OperStatus` 3 = up, PS1/PS2 | lab |
| Fan `rcChasFan*` | **absent on virtual** — hardware canary needed | lab |
| Port ifIndex | `1/1..` → 192+ | lab |
| `DESCRIPTION` column | media type (`1000BaseTX`), **not** user text | Fabric Engine 9.3 UG |
| MLT `name` max | 0–64 | Fabric Engine 9.3 UG |

The VOSS/Fabric Engine **CLI Commands Reference is not in the doc-to-rag corpus** — only the 9.3 User Guide. Worth ingesting.

## Zabbix

| Fact | Value | Source |
|---|---|---|
| Stock template has `{$NET.IF.IFALIAS.MATCHES}` / `.NOT_MATCHES` | yes, defaults `.*` / `CHANGE_IF_NEEDED` | git.zabbix.com extreme_snmp |
| `{#IFALIAS}` available as LLD macro | yes | same |
| `net.if.speed[ifHighSpeed…]` units | **bps** — custom multiplier 1000000 applied | same |
| Same item preprocessing | discard unchanged, heartbeat 1h | same |
| Master-branch template requires | **Zabbix 8.0+** — use release/7.0 branch | template README |
| Official AD DS / NTDS / DNS Server / DHCP Server template in 7.0 | **none** — `templates/app` has IIS/Exchange/SharePoint. Windows by agent is OS + Automatic services only. windows_exporter splits the same DC into `ad` + `dns` + `dhcp` | git.zabbix.com `templates/app` + `templates/os/windows_agent` on release/7.0; [ad-ds-coverage.md](ad-ds-coverage.md) |
| Official IIS template in 7.0 | **IIS by Zabbix agent** — W3SVC/WAS, port, `_Total` Web Service, app-pool LLD. **No TLS/cert expiry.** Do not scrape windows_exporter `iis`. Link on the hosts (not zerotouched) | git.zabbix.com `templates/app/iis_agent` release/7.0; [iis-coverage.md](iis-coverage.md) |
| Official website cert template in 7.0 | **Website certificate by Zabbix agent 2** — `web.certificate.get`; Warning at `{$CERT.EXPIRY.WARN}` default 7d; one hostname per host (no IIS binding LLD) | git.zabbix.com `templates/app/certificate_agent2` release/7.0 |
| Change-detect safety net | already exists as "Ethernet has changed to lower speed than it was before" (`change()<0`, ethernet ifTypes, manual close, **no settle**) | same |
| Per-interface link-down kill switch | `{$IFCONTROL:"{#IFNAME}"}` = 0 — keyed on ifName, not ifAlias. Not our mechanism | same |

## Consequence

EXOS `display-string` caps the grammar at **20 characters**. VOSS `name` allows 64, but the fleet grammar uses the lowest common denominator — **20**.

Because CLASS and SPEED come first in the grammar, truncation only ever damages the ID: a truncated `USW-10G-CH-ZRH-ZH4-D` still discovers correctly and still expects 10G. The generator must still enforce ≤20, because a truncated label produces a permanent generated-vs-live compliance diff.
