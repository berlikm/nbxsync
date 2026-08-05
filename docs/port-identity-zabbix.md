# Port identity — Zabbix LLD & triggers

How Zabbix applies the port label grammar from `docs/port-identity-foundation.md`.  
Label vocabulary and examples stay in the baseline; this doc is discovery and alerting behavior.

---

## 1. Resolution

```
1) Label empty → EMPTY; else parse class
2) Class X or N → no port alerts
3) Else include per role LLD (§2)
4) Discovered + {USW,US,UP,MON,UW} → link-down / flap / errors
5) Discovered + {USW,US,UP,MON} → expected speed = token or class default;
      ifHighSpeed ≠ expected ≥5m while oper-up → WARNING
6) Discovered + {USW,US,UP,MON,UW} → change(ifHighSpeed) vs last stable oper-up ≥5m → WARNING;
      suppress in maintenance windows
7) TMON → items + optional link-down INFO only (no speed / change WARN)
```

Turn on step 5 after labels for that site follow the grammar.

---

## 2. Role × LLD

| Device role | LLD |
|---|---|
| **Core / Dist / Mgmt** | Admin-up AND NOT class `X` AND NOT class `N` |
| **Access** | Include classes only (`USW` `US` `UP` `MON` `UW` `TMON`) |
| **Subsidiary hybrid** | TBD |
| **AP** | Device health — not switch-port LLD |

Unused ports → admin-down.

### Hybrid — TBD

Labeling rules for subsidiary hybrid (core∩access) are **not locked** yet.

```
# draft only — TBD
1) Spares / unused            → admin-down
2) Admin-up but uninteresting → X / X-<note> or N / N-<text>
3) Monitor / temp             → USW / US / UP / MON / UW / TMON / …
```
