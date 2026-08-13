# Network VMs

Prepared — same observability bar as [01-extreme-switching.md](01-extreme-switching.md). OS + ICMP already come from nbxSync. This page is only **network-critical** extras.

If the VM is down, switch/AP monitoring is blind. That is a symptom for **this** domain, not for 01.

---

## Observability

| Rule | Here |
|---|---|
| Page symptoms | VM unreachable; **service port down while host up**; cert about to expire |
| Graph causes | CPU, disk fill |
| One incident | Service check depends on host ICMP. Do not also page every switch when NetBox is down |
| Never silent | **Who watches Zabbix?** Self-monitoring is not enough — name an external check |
| Collect first | Explicit VM list before templates |

---

## What we alert

| Thing | Alert | Sev |
|---|---|---|
| Host unreachable | yes | High |
| Key service port down, host up | yes | High |
| Disk | yes | Warning |
| Cert expiring | yes | Warning — 30d |
| App health endpoint | yes | — |
| Backup / job freshness | later | silent failure today |

Do **not** alert on: the general server estate.

---

## Scope

| In | Out |
|---|---|
| NetBox, Zabbix, XIQ-SE, RADIUS/NAC, DHCP/IPAM, jump hosts, collectors | General servers |

Needs an **explicit list**.

---

## Dependencies

```
service port / HTTP  →  host ICMP  →  site
```

---

## Watch the watcher

| Check | Why |
|---|---|
| Zabbix proxy last-seen | already in 01; still required here |
| Zabbix server from **outside** | proxy cannot tell you the cloud UI is dead |
| NetBox HTTP | inventory + sync stop |

---

## Templates

| Template | Where |
|---|---|
| Linux / Windows by Zabbix agent | Platform Template Rules |
| Thin per-service (port / HTTP / cert) | Role or device |

---

## Later

Agree the VM list. Agent vs agentless. Overlap with whoever owns servers. Do not wait on this to cut over Extreme/APs — but the external Zabbix check should exist before we trust “all green.”
