# Plan: enable trigger dependencies on our stack

Goal: turn `trigger_dependencies.enabled` **on** and have it actually wire closet-kill **ICMP → ICMP** (AP → switch → gateway) together with inheritance (#115), TemplateRule (#117), bindings (#125), OOB (#129), and render (#110).

Non-goal: AP ICMP → switch port `UP-` / LLD link-down. That is a different feature (#100 matches one static trigger **name** per level). Do not stretch #100 to do it.

Until this plan is done, keep the flag **false**. HostSync must not depend on it.

---

## Architecture (one sentence)

**Inheritance is desired config. `ZabbixHostBinding` is identity. Trigger-dep is a post-sync policy.** Every consumer of “what is the Zabbix hostid?” must use one getter. #100 today reads the old column on a device-level assignment; that is why the flag is unsafe.

```
NetBox object
    │
    ├─ get_assigned_zabbixobjects()     → templates, IFs, server, exclude-tag
    ├─ get_managed_host_id(obj, server) → hostid  (binding, else legacy assignment.hostid)
    └─ after HostSync succeeds
           sync_device_trigger_dependencies(device)
               uses getter for child + cabled parents
               same Zabbix server only
               exact trigger name from config
```

---

## What lands in which PR

Do **not** stuff this into #115 (inheritance) or #117 (TemplateRule). A maintainer should see identity leftovers on **#125**, which is the PR that cleared `assignment.hostid`.

| PR | Role in this plan |
|---|---|
| **#122** | CI only. Land on 1.0.5 independently. Keep NetBox `v4.6.7` pin. |
| **#115** | Rebase only. Keep Site/Region `server_assignments` and `_prepare_assignment`. No trigger-dep body. |
| **#117** | Rebase only. TemplateRule decides which ICMP **name** exists; config must match it. |
| **#110** | Rebase only. Unrelated to triggers. |
| **#125** | **This is the adapter PR.** Identity getter + leftover readers (hostinfo, HostInterfaceSync extra_args, trigger-dep `get_host_assignments`) + synchost hook. |
| **#129** | Restack on #125. Pass `_instance` / binding hostid into interface sync (OOB already does `_instance`). |

Production stays on `cursor/all-in-one-e7f8` until the rebased stack exists. Optional: land the getter on all-in-one **before** the 1.0.5 rebase so Ops modal and direct-assignment IF sync start working in prod without waiting for upstream.

---

## Phase 0 — rebase onto 1.0.5 (no flag)

Already checked: merge is possible; **12 conflict files**. Hard file: `inheritance.py`.

Resolve rules (do not “accept theirs”):

- Keep **our** `inheritance.py` behaviour (`server_assignments`, inherited IFs, TemplateRule, Site chain). Fold in 1.0.5 `_macro_server_filter` if we do not already server-scope macros.
- Keep **our** `deletehost.py` / `sync_objects.py` (bindings).
- Keep **our** `synchost.py` loop; add the 1.0.5 hook later in Phase 2 (or add it disabled in the same rebase).
- Keep both settings trees: `trigger_dependencies` **and** `exclude_tag` / `allow_inherited_deletion` / `adopt_existing_hosts`. Do not reset background interval 360 → 60 unless we intend to.
- Take 1.0.5 `SyncMaintenanceJob` rename (already auto-merges with our worker).
- Take 1.0.5 hostinfo **loop** (multi-server, `fetch_errors`); still rewire hostid in Phase 1.

After Phase 0: production behaviour unchanged **if the flag stays false**.

---

## Phase 1 — identity getter (can ship before the flag)

Add to `nbxsync/utils/host_binding.py` (or a tiny `nbxsync/utils/host_identity.py` imported everywhere):

```python
def get_managed_host_id(instance, zabbixserver) -> int | None:
    binding = get_host_binding(instance, zabbixserver)
    if binding:
        return int(binding.hostid)
    # Legacy: only a *direct* assignment row, never a Site/Role row.
    ...
    return assignment.hostid or None

def iter_managed_servers(instance):
    """Servers this object is synced to: bindings ∪ inherited/direct assignments."""
    # union of iter_host_bindings(instance) and
    # get_assigned_zabbixobjects(instance)['server_assignments']
    # skip sync_enabled=False
```

Rewire **all** leftover `assignment.hostid` readers to this, in #125:

| Call site | Today | After |
|---|---|---|
| `synchost.py` HostInterfaceSync `extra_args` | `assignment.hostid` after `_clear_direct_hostid` → `None` on **direct** assignments | `get_managed_host_id(self.instance, assignment.zabbixserver)` |
| `HostSync.check_default_hostinterface` / `verify_hostinterfaces` | `if not self.obj.hostid: return` on a new instance that never called `_resolve_binding` | Call `_resolve_binding()` first, or pass hostid via extra_args |
| `views/hostinfo.py` | Device-level assignments + `assignment.hostid` | For each server from `iter_managed_servers`, `get_managed_host_id`. Keep 1.0.5 outer `event_list` / logging |
| API `ZabbixServerAssignment.hostid` | Null after first sync | Serializer: prefer binding for this assigned object; document assignment.hostid as legacy. Optional nested binding later |

This phase **already** fixes production: Ops problems/events, and direct-assignment interface reconcile. No 1.0.5 feature flag required.

**Tests (must fail on current all-in-one, pass after):**

1. Direct assignment: after `HostSync.sync()`, `assignment.hostid is None` and `get_managed_host_id(device, server) == binding.hostid`.
2. Inherited-only: assignment on Site, binding on device → getter returns binding hostid.
3. HostInterfaceSync extra_args after clear still creates/updates against that hostid.
4. Hostinfo with binding only returns rows (mocked API).

---

## Phase 2 — teach #100 the getter + hook

Only after Phase 0 (module exists) and Phase 1 (getter exists).

**`trigger_dependency_sync.py`**

- Replace `get_server_assignments` / `get_host_assignments` internals. Keep the same return shape if possible (`{zabbixserver_id: object with .hostid and .zabbixserver}`) so `_prepare_child_dependency_sync` stays small.
- Child and each parent: `get_managed_host_id`. No device-level assignment required.
- Keep: complete `_path` only, role token set intersection, same server, exact `description` match, preserve unmanaged deps, idempotent update.

**`synchost.py` hook** (our 300-line job, not 1.0.5’s 105-line loop):

```python
# after the assignment for-loop, before _raise_on_partial_failure
td = getattr(pluginsettings, 'trigger_dependencies', None)
if (
    object_type == 'device'
    and zabbix_status != ZabbixHostStatus.DELETED
    and td is not None
    and td.enabled
):
    try:
        sync_device_trigger_dependencies(self.instance)
    except Exception:
        logger.exception('Trigger dependency sync failed for %s; continuing.', self.instance)
```

Do **not** call on the exclude-tag return path. Do **not** call for VMs. `getattr` so a mixed tree cannot `AttributeError`.

**Settings:** 1.0.5 `TriggerDependencyConfig` + `7c0b534` validators already sit beside our flags after a correct Phase 0 merge. Default `enabled: False`.

**Tests:**

5. Binding + cleared assignment.hostid → `get_host_assignments` still has the host (today: `{}`).
6. Inherited-only device → same (today: empty because `assigned_object_id=device.pk`).
7. Hook called once when enabled; not called when disabled / VM / DELETED / exclude-tag.
8. Missing `trigger_dependencies` on settings → synchost does not AttributeError.
9. Wrong trigger name → warning, no `trigger.update`, HostSync still succeeds.
10. `Switch Access` vs default token `switch` → no level (documents config, not a code bug).

Upstream tests that assert `assigned_object_id=42` must be **updated** in #125 to the getter behaviour, or they will lock in the no-op.

---

## Phase 3 — estate config (not a plugin PR)

#100 will no-op on our names with stock defaults. This is NetBox `PLUGINS_CONFIG`, not Extreme YAML.

Role tokens must be **full** names/slugs (`switch` ≠ `Switch Access`):

```yaml
trigger_dependencies:
  enabled: false   # flip true only after Phase 2 + lab
  levels:
    - name: access_point
      roles: ['access point', 'access-point', 'ap']
      trigger_description: 'Extreme IQ Engine: Unavailable by ICMP ping'  # confirm exact Zabbix name
    - name: switch
      roles: ['switch access', 'switch dist', 'switch core', 'switch mgmt', 'switch']
      trigger_description: '<ONE ICMP name>'  # EXOS and VOSS cannot share a level unless names match
    - name: gateway
      roles: ['gateway', 'firewall', 'router', ...]
      trigger_description: '<gateway ICMP name>'
```

Constraint: **one level = one trigger name.** If EXOS ICMP ≠ VOSS ICMP, they cannot both be “the switch level.” Options: (a) make template trigger names identical, (b) only enable deps for the platform whose name you put in config, (c) later feature (out of scope). Do not invent two switch levels — level **index** is parent/child, not vendor.

Cables: NetBox `_path` must be **complete**. Incomplete traces skip with a warning.

Lab sequence: one AP + one switch, complete cable, matching roles, matching names, flag on, sync AP (and/or switch). Zabbix: AP ICMP trigger depends on switch ICMP trigger. Then enable in prod.

---

## Phase 4 — turn the flag on

1. Phase 1+2 merged to all-in-one (and/or rebased #125).
2. Tests 1–10 green.
3. Lab closet-kill proven.
4. `enabled: true` in lab `PLUGINS_CONFIG`, restart NetBox.
5. Watch logs: `No Zabbix host assignment with hostid found` must **stop** for bound inherited devices. Remaining skips = incomplete cables / role miss / wrong name (config, not code).
6. Prod: same YAML, same flag. HostSync still succeeds if Zabbix trigger-dep API fails (hook `try/except`).

---

## What “working all together” means

| Piece | Interaction with trigger-dep |
|---|---|
| #115 inheritance | Getter uses binding on the **device**, not Site assignment.hostid (never written). |
| #117 TemplateRule | Supplies the trigger **name** that `trigger_description` must equal. |
| #110 render | None. |
| #125 bindings | Source of hostid. `_clear_direct_hostid` stays; readers must not use that column. |
| #129 OOB | None for topology. Interface extra_args must use getter so OOB IF still lands on the right host. |
| exclude-tag | Hook skipped; hosts deleted. |
| allow_inherited_deletion / adopt_existing_hosts | Unrelated; stay default-off. |

Still skipped (by design): VMs, incomplete cables, parent on another Zabbix server, unmatched roles, `UP-` LLD.

---

## Suggested execution order

1. **Now (all-in-one, optional but best for prod):** Phase 1 getter + hostinfo + IF extra_args. Flag still absent/off. Ops modal starts working.
2. **Rebase** all-in-one / stack onto `upstream/development` (Phase 0). Flag still false.
3. **#125 on that rebase:** Phase 2 rewire + hook. Restack #129.
4. **Lab config** (Phase 3) then **enable** (Phase 4).

Do not enable the flag at step 2. Do not put the rewire in #115.
