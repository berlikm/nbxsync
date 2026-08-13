# Runbook — phased onboarding (exclude most, enable one-by-one)

During cutover many NetBox objects are **inventory-true but not monitorable yet** (Zabbix agent missing, wrong credentials, not reachable). Keep the estate quiet, then open hosts deliberately.

**Folder map:** [`../configuration.md`](../configuration.md) (§9 exclude, §12 plugin) · Troubleshoot: [`day2.md`](day2.md)

---

## Mechanism (NetBox tag switch — no plugin change)

Plugin setting `exclude_tag` = `do_not_monitor` — unchanged.

| Intent | How |
|---|---|
| **Onboarding / not ready** | NetBox inventory tag **`onboarding`** on the Device/VM. Once: assign Zabbix tag `do_not_monitor` on the **NetBox Tag** object (Tag → Zabbix tab). Every host carrying `onboarding` inherits exclude. |
| **Permanent never-monitor** | Zabbix tag `do_not_monitor` on the **Device Role** (Messpc, Sd Wan Socket, VDI) |

**Enable a host:** remove NetBox tag **`onboarding`** from that Device/VM → next sync creates/updates the Zabbix host.

Sync **skips** excluded objects (no Zabbix host; an existing one is deleted).

Do **not** put `do_not_monitor` on a Site Group or on role **Server** for waves. Inheritance would lock the whole class out; you cannot “open” a single child while the parent still excludes.

---

## One-time setup

1. Plugin `exclude_tag` = `do_not_monitor` (already).
2. Create NetBox tag **`onboarding`** (zerotouch step 0).
3. Organization → Tags → **onboarding** → Zabbix tab → Tags → assign **`do_not_monitor`** (zerotouch step 9).
4. Permanent roles keep role-level Zabbix `do_not_monitor` (Messpc, Sd Wan Socket, VDI).

---

## Recommended waves

Policy (Servers through Macros) can be fully built first. Hosts only appear in Zabbix when they are **not** excluded.

| Wave | What | Why |
|---|---|---|
| **0 — Policy** | Servers, proxies, CGs, Template Rules, hostgroups, macros | No host noise yet if agent fleet carries `onboarding` |
| **1 — SNMP-ready** | Switch*, AP, Firewall, OOB/storage SNMP, … | No agent; credentials + reachability are enough |
| **2 — Agent hosts** | Servers / VMs / SPACE / … | Enable only after agent installed and reachable |
| **3 — Overlays** | `snmp` / `oracle` / `critical` where needed | Opt-in transport and hostgroups on already-synced hosts |

Adjust wave order to your cutover; the switch is always: **add/remove NetBox tag `onboarding`**.

---

## Bulk exclude (agent fleet)

1. Confirm setup above (NetBox tag `onboarding` has Zabbix `do_not_monitor` assigned).
2. Permanent roles already have the role-level assignment — leave them.
3. For every Device/VM that should **not** sync yet (typical: agent-class with status `active` but agent not ready):
   - NetBox → object → **Tags** → add **`onboarding`**
   - Or bulk via NetBox UI / API tag edit.
4. Re-sync (or wait for the job cycle). Those objects stay out of Zabbix.

SNMP classes you want live in wave 1: **do not** assign `onboarding` on them.

---

## Enable one host

When that object is ready to monitor:

1. **Ready check** (integration gate — keep short):
   - Site / country Site Group resolves
   - Primary IP (and `oob_ip` if BMC) set
   - Agent installed and reachable **or** SNMP credentials match the CG
   - Not on a permanently excluded role
2. Open the Device/VM in NetBox → **remove tag `onboarding`**.
3. Re-sync that host (or wait for the background cycle).
4. Compare to configuration **§13**. If wrong, use [`day2.md`](day2.md) host-not-monitored.

No new configuration group or Template Rule is required for a normal agent host — Site Group Agent default already covers it once exclusion is gone.

---

## What not to use for this problem

| Approach | Why it is a poor fit here |
|---|---|
| Role-level `do_not_monitor` on Server / VM roles | Cannot enable a single host until the whole role is opened |
| Per-device Zabbix-tab `do_not_monitor` for waves | Works, but harder to bulk-edit than a NetBox inventory tag — prefer `onboarding` |
| NetBox status `planned` / `staged` → Zabbix disabled | Host still created; meant for lifecycle status, not “agent not installed” |
| Soft-state / `NO_ALERTING` | Host still polled; different problem |
| Removing Agent CG from the country Site Group | Stops **everyone**; too coarse for one-by-one |
| Plugin changes / second `exclude_*` setting | Not needed — Tag-targeted Zabbix assignments already inherit |

---

## After go-live

- New objects that are not ready yet: add NetBox tag `onboarding` at create time (or leave them until ready — if Agent default would sync them immediately, prefer tag-first).
- Permanent never-monitor classes: keep **role-level** Zabbix tag `do_not_monitor` only.
- Day-2 policy changes: [`day2.md`](day2.md).
