# Runbook — phased onboarding (exclude most, enable one-by-one)

During cutover many NetBox objects are **inventory-true but not monitorable yet** (Zabbix agent missing, wrong credentials, not reachable). Keep the estate quiet, then open hosts deliberately.

Policy: [`../configuration.md`](../configuration.md) (§9 exclude, §12 plugin). Troubleshoot: [`day2.md`](day2.md).

---

## Mechanism (NetBox tag switch)

Plugin setting `exclude_tag` = `do_not_monitor`.

| Intent | How |
|---|---|
| **Onboarding / not ready** | NetBox inventory tag **`onboarding`** on the Device/VM. Once: assign Zabbix tag `do_not_monitor` on the **NetBox Tag** object (Tag → Zabbix tab). Every host carrying `onboarding` inherits exclude. |
| **Permanent never-monitor** | Zabbix tag `do_not_monitor` on the **Device Role** (Messpc, VDI) |
| **Cato Socket controlled release** | All 21 current Socket hosts are live. Add `onboarding` before a new or replacement Socket's first sync; release it only after its primary IP and proxy path are ready. |

**Enable a host:** remove NetBox tag **`onboarding`** from that Device/VM → next sync creates/updates the Zabbix host.

Sync **skips** excluded objects (no Zabbix host; an existing one is deleted).

Do **not** put `do_not_monitor` on a Site Group or on role **Server** for waves. Inheritance would lock the whole class out; you cannot “open” a single child while the parent still excludes.

---

## One-time setup

1. Plugin `exclude_tag` = `do_not_monitor` (§12).
2. Create NetBox tag **`onboarding`**.
3. Organization → Tags → **onboarding** → Zabbix tab → Tags → assign **`do_not_monitor`**.
4. Permanent roles keep role-level Zabbix `do_not_monitor` (Messpc, VDI),
   except for the explicitly deferred Cato Socket rollout below.
5. The Cato account collector is live. Refresh it with
   `configure_nbxsync_network.py --apply-cato` (not zerotouch). Socket
   migration is deliberately deferred; do **not** run
   `configure_nbxsync_zerotouch.py --enable-cato --mutate-netbox` in the
   current rollout.

---

## Recommended waves

Policy (Servers through Macros) can be fully built first. Hosts only appear in Zabbix when they are **not** excluded.

| Wave | What | Why |
|---|---|---|
| **0 — Policy** | Servers, proxies, CGs, Template Rules, hostgroups, macros | No host noise yet if agent fleet carries `onboarding` |
| **1 — SNMP-ready** | Switch*, AP, Firewall, OOB/storage SNMP, … | No agent; credentials + reachability are enough |
| **2 — Agent hosts** | Servers / VMs / SPACE / … | Enable only after agent installed and reachable |
| **3 — Overlays** | `snmp` / `oracle` / `critical` where needed | Opt-in transport and hostgroups on already-synced hosts |
| **4 — Cato Sockets** | One Socket at a time after migration | Primary IP and regional proxy path must be ready; use the controlled command below. |

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

Generic bulk sweeps must not tag, untag, hold, or release `Sd Wan Socket`;
Cato uses the controlled-release procedure below after its separately approved
migration.

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

## Cato Socket hold and release

**Current production state (2026-08-25):** all 21 Cato Sockets are live with
one stock `ICMP Ping` host each. None carries `onboarding` or the legacy
inventory `do_not_monitor` tag, and the role-level exclusion is absent.

For every new or replacement Socket, perform this operator-owned NetBox action
immediately after it appears in NetBox, before its first nbxSync run. The
command is idempotent: `hold` adds `onboarding`, and `release` removes it only
when the Socket has a primary IPv4 address. It always runs one `SyncHostJob`
for that Socket.

Run from `/opt/netbox/netbox` after sourcing `/etc/netbox.env`:

```bash
export CATO_SOCKET='CH-NKN-CATO01'
export CATO_ACTION='hold'
PYTHONPATH=. DJANGO_SETTINGS_MODULE=netbox.settings \
  /opt/netbox/venv/bin/python3 -c '
import django, os; django.setup()
from dcim.models import Device
from extras.models import Tag
from nbxsync.jobs.synchost import SyncHostJob
action = os.environ["CATO_ACTION"]
assert action in {"hold", "release"}
device = Device.objects.get(name=os.environ["CATO_SOCKET"], role__slug="sd-wan-socket")
onboarding = Tag.objects.get(slug="onboarding")
if action == "hold":
    device.tags.add(onboarding)
else:
    assert device.primary_ip4 is not None
    device.tags.remove(onboarding)
SyncHostJob(instance=device).run()
'
```

For a new or replacement Socket, set `CATO_ACTION=release` only after the
NetBox primary IP and regional proxy route are ready. Verify the resulting host
has one primary-IP Agent interface, stock `ICMP Ping`, exactly one `icmpping`,
and tags `component=cato`, `monitoring_domain=cato_socket`. Do not attach the
Cato account template to a Socket host.

---

## What not to use for this problem

| Approach | Why it is a poor fit here |
|---|---|
| Role-level `do_not_monitor` on Server / VM roles | Cannot enable a single host until the whole role is opened |
| Role-level `do_not_monitor` on `Sd Wan Socket` | Must remain absent: it blocks controlled per-Socket release and duplicates the onboarding hold. |
| Per-device Zabbix-tab `do_not_monitor` for waves | Works, but harder to bulk-edit than a NetBox inventory tag — prefer `onboarding` |
| NetBox status `planned` / `staged` → Zabbix disabled | Host still created; meant for lifecycle status, not “agent not installed” |
| Soft-state / `NO_ALERTING` | Host still polled; different problem |
| Removing Agent CG from the country Site Group | Stops **everyone**; too coarse for one-by-one |

---

## After go-live

- New objects that are not ready yet: add NetBox tag `onboarding` at create time (or leave them until ready — if Agent default would sync them immediately, prefer tag-first).
- New Cato Socket: set `CATO_ACTION=hold` before its first nbxSync run, then
  release only when its primary IP and proxy path are ready.
- Permanent never-monitor classes: keep **role-level** Zabbix tag
  `do_not_monitor` only on Messpc and VDI.
- Day-2 policy changes: [`day2.md`](day2.md).
