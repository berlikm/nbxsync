# Runbook — nbxSync day-2 operations

Operator procedures after the initial nbxSync build ([configuration checklist](../configuration.md) §§1–13 + plugin settings §12).

Mental model: [`../architecture.md`](../architecture.md).  
Expected host state: checklist **§13**.  
Extreme domain steps: [`../../../zabbix/01-extreme-switching.md`](../../../zabbix/01-extreme-switching.md), [`../../../zabbix/port-identity.md`](../../../zabbix/port-identity.md).

**Assumption:** NetBox inventory already has role / platform / site / IP / tags. This runbook changes **nbxSync policy** (and checks sync results) — not inventoring NetBox.

---

## 1. New Device Role appeared

1. Does it need a **transport exception**?
   - Agent-class → nothing (Site Group Agent default); if ICMP Ping should apply, extend TemplateRule **Agent Host ICMP** `role_pattern` (checklist §6.3)
   - Network SNMP → **SNMP Monitoring**
   - SPACE → **Agent Monitoring (SPACE)**
   - Dual-plane BMC server → **Server Agent+OOB**
   - SAP dual-plane → **SAP Agent+SNMP** (one CG with Agent + SNMP — not SNMP-only, not two CGs)
   - ESXi hosts → role **ESXi Hypervisor** + CG **ESXi OOB iDRAC** (SNMPv2c `public` @ oob)
   - OOB-only → **OOB SNMP Only**
   - Linux SNMP opt-in → NetBox tag `snmp` (no new role CG)
2. Does it need an **application template**? Add a Template assignment on the role (checklist §7).
3. New **Switch*** role? Copy IFALIAS / IFTYPE macros from the closest peer (`zabbix/01-extreme-switching.md` §5 / §8; nbxSync assignments per checklist §11.1). Platform Template Rules already cover EXOS/VOSS (EXOS rule from network script).
4. Hostgroup `Roles/<name>` appears automatically from the Sites/Roles Jinja — do **not** create a per-role hostgroup assignment.

---

## 2. New Extreme switch

On-box labels and stages: [`zabbix/01-extreme-switching.md`](../../../zabbix/01-extreme-switching.md), [`port-identity.md`](../../../zabbix/port-identity.md).

With role / platform / site / primary IP already in NetBox, sync should match the Extreme switch rows in checklist **§13**. IFALIAS assignments: checklist §11.1.

If VOSS still gets Network Generic, fix checklist §6.1 (YAML missing or onboarding re-run left the placeholder — see [`scripts/README.md`](../../../scripts/README.md)).

---

## 3. Extreme staged enablement

Stages and Hybrid flip: Extreme doc §7.  
nbxSync clicks at those stages: checklist §7.1 and §11.1.

---

## 4. New Platform appeared

1. Does an existing Template Rule pattern already match? Check with the real platform name (regex `search`).
2. If not, add or extend a rule in checklist §6 (every matching rule contributes — do not rely on priority to suppress another rule’s different template).
3. Confirm the template’s **interface requirements** match the transport the host will have.
4. **ESXi / VMware:** transport CG **ESXi OOB iDRAC** is on role **ESXi Hypervisor** (platform-level ESXi OOB assignments are pruned). New ESXi devices need that **role** (zerotouch `--mutate-netbox` migrates matching platforms off Server). Dell → Dell iDRAC (ESXi) Template Rule. Do **not** re-enable legacy **VMware ESXi** or a VMware FQDN platform rule — keep VMware FQDN on role **vCenter** only.

---

## 5. New application template

1. Import/create the template in Zabbix; create the nbxSync Template object.
2. Set interface requirements (Agent / SNMP / ANY).
3. Assign on the Device Role (or Device type / Manufacturer if that is the true scope) — checklist §7.

---

## 6. Host not monitored / wrong templates

Work top-down:

1. **Excluded?** NetBox tag `onboarding` (inherits Zabbix `do_not_monitor` from the Tag) and/or role-level Zabbix `do_not_monitor` — see [`onboarding.md`](onboarding.md).
2. **Site / Site Group?** Device or VM must resolve into a managed country (site set; cluster VMs need site or cluster site scope). No site → not profiled (checklist §13).
3. **Effective configuration group?** On the device/VM Zabbix tab (or inherited from role / Site Group). Wrong CG → wrong interfaces.
4. **Interfaces present?** Agent and/or SNMP as expected; for BMC / ESXi, is `oob_ip` set? ESXi should be role **ESXi Hypervisor** + SNMPv2c **`public` @ oob** only (no agent, not Server Agent+OOB / MONITORING-DELL).
5. **Template interface requirements?** Template needing Agent will not link on an SNMP-only host (silent drop) — checklist §7.
6. **Template Rules?** Platform name vs rule regex; `require_tags` (e.g. `snmp`); enabled flag. Remember all matching rules apply.
7. **Status mapping?** Planned/offline/etc. may disable or delete the Zabbix host (checklist §12).
8. Re-sync the host and compare to the checklist §13 expected-state row for that class.

---

## 7. Recurring manual checks

| Task | When |
|---|---|
| Cohesity VMs with primary IP → SNMP Monitoring (checklist §5b) | When such VMs are created or found |
| Extreme port labels / Hybrid flip / stage gates | Per [`zabbix/01-extreme-switching.md`](../../../zabbix/01-extreme-switching.md) and [`port-identity.md`](../../../zabbix/port-identity.md) |
| Spot-check `environment=Unknown` | After naming-convention drift |
| No manufacturer Huawei SNMP CG; no per-device HI on `HU-DEB-SAN01`; no leftover CG named `SNMP Monitoring (SAP)` | After zerotouch / credential changes |
| ESXi still on role **ESXi Hypervisor** with SNMPv2c `public` (not Server / MONITORING-DELL) | After role or platform inventory drift |
| Update “Last verified” stamp on the [configuration checklist](../configuration.md) | After a production re-validation |
