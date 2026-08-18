# EXOS `net.if.discovery` empty (DIST/ACCE canary)

**Symptom:** VOSS hosts have dozens of `net.if.*` items; EXOS DIST/ACCE show ~30–35 items and **0** `net.if.*`.

## Macro names are not the bug

Stock Extreme EXOS LLD already uses the same names we assign:

| Filter macro | Stock default | Our Dist/Core | Our Access |
|---|---|---|---|
| `{$NET.IF.IFALIAS.MATCHES}` | `.*` | `.*` | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` |
| `{$NET.IF.IFALIAS.NOT_MATCHES}` | `CHANGE_IF_NEEDED` | `^X(-\|$)` | `CHANGE_IF_NEEDED` |
| `{$NET.IF.IFTYPE.MATCHES}` | `.*` | `^(6\|161)$` | `^(6\|161)$` |
| `{$NET.IF.IFADMINSTATUS.NOT_MATCHES}` | `^2$` | (template) | (template) |
| `{$NET.IF.IFOPERSTATUS.NOT_MATCHES}` | `^6$` | (template) | (template) |

There is no separate “template uses IFNAME only” path for EXOS IF LLD.

## Expected vs broken

| Host role | Labels on box | `net.if.*` count | Verdict |
|---|---|---|---|
| **Access / Hybrid** | none / no USW\|… | **0** | **Expected** — opt-in filter |
| **Access** | some `UP-…` / `USW-…` | >0 for those ports | OK |
| **Dist / Core / Mgmt** | any (incl. empty) | **0** | **Broken** — LLD not succeeding or wrong role macros |
| Dist/Core | empty + admin-up eth | >0 | OK |

## Likely causes when Dist = 0

1. **Stock LLD interval 1h** — discovery not run yet after template link.  
   Fix: `configure_nbxsync_network.py` patches delay **15m**, disable-lost immediately, delete after **7d**; then **Execute now** on the host rule.
2. **Discovery rule error** — heavy multi-OID IF-MIB walk times out (Fan/PSU use lighter Extreme OIDs and still work).  
   Check: host → Discovery rules → `Network interfaces discovery` → error text / SNMP timeout on proxy.
3. **Wrong role macros** — Dist host still has Access `MATCHES=^(USW|…)` and no labels.  
   Check host macros; re-apply network script + sync.
4. **All ports admin-down** — stock `IFADMINSTATUS.NOT_MATCHES=^2$` drops them (by design).

## Ops checks (DIST01)

1. Host macros: `IFALIAS.MATCHES=.*`, `NOT_MATCHES=^X(-|$)`, `IFTYPE.MATCHES=^(6|161)$`.
2. Discovery rule state/error for `net.if.discovery`.
3. Execute now; confirm items appear within one cycle.
4. If timeout: raise proxy/host SNMP timeout for that walk, or poll fewer OIDs later (thin template) — do not clone stock.
