# Runbook — phased onboarding (exclude most, enable one-by-one)

During cutover many NetBox objects are **inventory-true but not monitorable yet** (Zabbix agent missing, wrong credentials, not reachable). Keep the estate quiet, then open hosts deliberately.

**Folder map:** [`../README.md`](../README.md) · **Exclude mechanics:** [`../configuration.md`](../configuration.md) §9.3 / §12 · **Troubleshoot:** [`day2.md`](day2.md) §6

---

## Mechanism (one switch)

Plugin setting `exclude_tag` = `do_not_monitor` (configuration §12).

Exclusion is a **nbxSync Zabbix tag assignment** (`ZabbixTag` name `do_not_monitor`) on the Device, VM, or Role — **not** a NetBox inventory tag. Sync then **skips** the object (no Zabbix host; an existing one is deleted).

| Scope | Use for |
|---|---|
| **Device / VM** (object-level) | Onboarding waves — exclude many, enable **one by one** |
| **Device Role** | Permanent classes that never sync (Messpc, Sd Wan Socket, VDI) |

Do **not** put `do_not_monitor` on a Site Group or on role **Server** for waves. Inheritance would lock the whole class out; you cannot “open” a single child while the parent still excludes.

---

## Recommended waves

Policy (configuration §§1–13) can be fully built first. Hosts only appear in Zabbix when they are **not** excluded.

| Wave | What | Why |
|---|---|---|
| **0 — Policy** | Servers, proxies, CGs, Template Rules, hostgroups, macros | No host noise yet if agent fleet is excluded |
| **1 — SNMP-ready** | Switch*, AP, Firewall, OOB/storage SNMP, … | No agent; credentials + reachability are enough |
| **2 — Agent hosts** | Servers / VMs / SPACE / … | Enable only after agent installed and reachable |
| **3 — Overlays** | `snmp` / `oracle` / `critical` where needed | Opt-in transport and hostgroups on already-synced hosts |

Adjust wave order to your cutover; the switch is always the same: **object-level exclude on / off**.

---

## Bulk exclude (agent fleet)

1. Confirm Zabbix tag `do_not_monitor` exists and plugin `exclude_tag` is set (configuration §9.3 / §12).
2. Permanent roles already have the role-level assignment — leave them.
3. For every Device/VM that should **not** sync yet (typical: agent-class with status `active` but agent not ready):
   - NetBox → object → **Zabbix** tab → Tags → assign **`do_not_monitor`**
   - Or bulk via NetBox API / a one-shot script creating `ZabbixTagAssignment` rows (object-level only).
4. Re-sync (or wait for the job cycle). Those objects stay out of Zabbix.

SNMP classes you want live in wave 1: **do not** assign the exclude tag on them.

---

## Enable one host

When that object is ready to monitor:

1. **Ready check** (integration gate — keep short):
   - Site / country Site Group resolves
   - Primary IP (and `oob_ip` if BMC) set
   - Agent installed and reachable **or** SNMP credentials match the CG
   - Not on a permanently excluded role
2. Open the Device/VM → **Zabbix** tab → remove the **`do_not_monitor`** tag assignment.
3. Re-sync that host.
4. Compare to configuration **§13** (expected CG / templates / interfaces). If wrong, use [`day2.md`](day2.md) §6.

No new configuration group or Template Rule is required for a normal agent host — Site Group Agent default already covers it once exclusion is gone.

---

## What not to use for this problem

| Approach | Why it is a poor fit here |
|---|---|
| Role-level `do_not_monitor` on Server / VM roles | Cannot enable a single host until the whole role is opened |
| NetBox status `planned` / `staged` → Zabbix disabled | Host still created; meant for lifecycle status, not “agent not installed” |
| Soft-state / `NO_ALERTING` | Host still polled; different problem |
| Removing Agent CG from the country Site Group | Stops **everyone**; too coarse for one-by-one |

---

## After go-live

- New objects that are not ready yet: assign object-level `do_not_monitor` at create time (or leave them until ready — if Agent default would sync them immediately, prefer exclude-first).
- Permanent never-monitor classes: keep **role-level** assignment only.
- Day-2 policy changes: [`day2.md`](day2.md).
