# Runbook — nbxSync day-2

After the first build. Inventory (role / platform / site / IP / tags) is already in NetBox. This page only changes **nbxSync policy** and checks the Zabbix host.

Object map: [README.md](../README.md). Expected host: [objects/11-host-result.md](../objects/11-host-result.md).

---

## 1. New Device Role

1. Transport exception?
   - Agent-class → nothing (Site Group Agent default). If ICMP should apply, extend Template Rule **Agent Host ICMP** `role_pattern`.
   - Network SNMP → CG **SNMP Monitoring**
   - SPACE → **Agent Monitoring (SPACE)**
   - SAP → **SAP Agent+SNMP** (one CG, both interfaces)
   - iDRAC → **Dell iDRAC SNMP** on ESXi Hypervisor; **Legacy** on Cohesity; AES128 on listed KR/CN devices. Server stays Site Group Agent.
   - Linux SNMP opt-in → tag `snmp`
2. Application template? Assign on the role (Templates article).
3. New Switch* role? Copy IFALIAS / IFTYPE macros from the closest peer (Extreme switching + Macros article). Platform Template Rules already cover EXOS/VOSS.
4. Hostgroup `Roles/<name>` appears from Sites/Roles Jinja — do not create a per-role hostgroup assignment.

---

## 2. New Extreme switch

Role / platform / site / primary IP in NetBox. Sync should match the switch row in the host-result article. If VOSS still gets Network Generic, the YAML is missing or the network script was not run after zerotouch.

---

## 3. Extreme staged enablement

Stages and Hybrid flip: Extreme switching doc. nbxSync side: Templates (capability templates on the role) and Macros (IFALIAS on Switch*).

---

## 4. New Platform

1. Does an existing Template Rule already match the real platform name?
2. If not, add or extend a rule. Every matching rule contributes.
3. Template interface requirements must match the host transport.
4. ESXi: role **ESXi Hypervisor**, CG Dell iDRAC SNMP @ oob_ip. Do not re-enable VMware ESXi platform rule. VMware FQDN stays on role **vCenter**.

---

## 5. New application template

1. Import in Zabbix; create the nbxSync Template object.
2. Set interface requirements (Agent / SNMP / ANY).
3. Assign on the Device Role (or Device type / Manufacturer if that is the true scope).

---

## 6. Host not monitored / wrong templates

1. Excluded? NetBox tag `onboarding` and/or role-level `do_not_monitor`.
2. Site / Site Group? No site → not profiled.
3. Winning configuration group (Device Zabbix tab). Wrong CG → wrong interfaces.
4. Interfaces: Agent and/or SNMP as expected. iDRAC needs `oob_ip`. AES128 exceptions: device CG, no durable per-device HostInterface.
5. Template needs Agent but host is SNMP-only → silent drop.
6. Template Rules: platform vs regex; `require_tags`; enabled. All matching rules apply.
7. Status mapping (plugin settings) may disable or delete the host.
8. Re-sync and compare to the host-result row for that class.

---

## 7. Recurring checks

| Task | When |
|---|---|
| Cohesity VMs with primary IP → SNMP Monitoring | New Cohesity Appliance VMs |
| Extreme labels / Hybrid / stages | Extreme switching doc |
| `environment=Unknown` on hosts that should have `-p-` | Naming drift (switches without `-p-` are expected Unknown) |
| No manufacturer Huawei SNMP CG; no per-device HI on HU-DEB-SAN01; no CG `SNMP Monitoring (SAP)`; no tag `snmp-sap` | After zerotouch |
| Tag `onboarding` still has Zabbix `do_not_monitor`; ready hosts have the NetBox tag removed | Cutover waves |
| iDRAC: ESXi AES256 / KR-CN AES128 / Cohesity Legacy; no leftover Dell iDRAC HTTP | After CG / credential changes |
