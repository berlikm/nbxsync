# Dell iDRAC / OOB scoping — options analysis

**Problem:** Manufacturer Dell → Dell iDRAC by SNMP is fully automated for new Dell servers, but inheritance is **additive**. Any Dell device that ends up with an SNMP interface also inherits iDRAC (storage OEM models, mis-roled switches, Cohesity nodes, …). Device type can **add** HP MSA (etc.); it cannot remove iDRAC. Interface requirements only gate Agent vs SNMP — they do not separate two SNMP templates.

**Goal:** Keep **zero-touch for new Dell servers with BMC**, avoid iDRAC on Dell hardware that should not have it, scale with fleet growth (thousands of devices), stay within (or minimally extend) nbxsync.

---

## Constraints (from lab + code)

| Fact | Implication |
|---|---|
| Template resolution merges by template ID | No “Device type overrides Manufacturer” |
| `interface_requirements` | Drops template if IF type missing; both iDRAC and MSA need SNMP → both can link |
| `oob_ip` empty | Skips OOB SNMP **interface**; iDRAC template may still remain eligible |
| TemplateRule criteria | Platform regex **and** optional `role_pattern` **and** optional `require_tags` (NetBox tags on the **Device/VM**) |
| TemplateRule has **no** Manufacturer / DeviceType / `oob_ip` criterion today | Cannot express “Dell ∧ Server” in one rule without a tag or listing models |
| ConfigGroup templates | Expand onto hosts that resolve that CG — still no vendor filter |
| Org is flat | No regional RBAC trick to hide the problem |

---

## Option A — Keep Manufacturer Dell (status quo)

**How:** iDRAC on Manufacturer; OEM on Device type; live with both on storage.

| | |
|---|---|
| Scales | Excellent for “new Dell server” |
| Correctness | Poor for mixed Dell estate (storage / appliances) |
| Ops cost | Low until collisions; then high (Storage Generic-style workarounds) |
| Plugin change | None |

**Verdict:** Fine only if almost all Dell objects that get SNMP are true BMC servers. Lab already showed that is not true.

---

## Option B — Device type list (Dell server models only)

**How:** Remove Manufacturer iDRAC. Assign iDRAC on each Dell **server** Device type (R640, R740, …). Storage DTs get MSA/Storage Generic only.

| | |
|---|---|
| Scales | With **models** (~dozens), not hosts — acceptable |
| Correctness | Excellent if DT hygiene is good |
| Ops cost | New Dell server model → one NetBox row (checklist / script) |
| Miss risk | New DT forgotten → server has OOB IF but no iDRAC template |
| Plugin change | None |

**Verdict:** Strong baseline. Boring, predictable, no new concepts. Pair with a periodic “Dell server DT without iDRAC assignment” audit.

---

## Option C — Role Server (or Server Agent+OOB ConfigGroup) only

**How:** iDRAC on Device Role `Server`, or as a template on configuration group **Server Agent+OOB**.

| | |
|---|---|
| Scales | Excellent |
| Correctness | **Wrong for multi-vendor servers** — HPE/Lenovo Server role would get **Dell** iDRAC |
| Works when | Server role (or that CG) is Dell-only in practice |
| Plugin change | None |

**Verdict:** Reject as sole mechanism unless estate is Dell-only for that role. Attractive coupling of “BMC transport profile ↔ BMC template” but vendor-blind.

---

## Option D — NetBox tag `idrac` / `bmc` + TemplateRule

**How:**

1. Remove Manufacturer iDRAC (or leave it off).
2. TemplateRule: `pattern=.*`, `role_pattern=Server` (and any other BMC roles), `require_tags=idrac`, template = Dell iDRAC, priority low.
3. Ensure Dell servers carry NetBox tag `idrac` (bulk today; on create going forward).

| | |
|---|---|
| Scales | Excellent **if tagging is automated** |
| Correctness | Excellent — conjunctive role ∧ tag; storage without tag never matches |
| Ops cost | Tag discipline; or one automation |
| Plugin change | None (uses existing compound rules) |
| Failure mode | Untagged Dell server → OOB IF yes, iDRAC template no (visible gap) |

**Tag application strategies (pick one):**

| Strategy | Scale | Notes |
|---|---|---|
| D1 Manual / bulk edit | Weak | Re-creates membership work |
| D2 Checklist script stamps Dell+Server | Good | Same place as zero-touch configure |
| D3 NetBox event rule / custom script on Device save | Best | Manufacturer=Dell ∧ role∈BMC → add tag; storage roles skip |
| D4 Tag on Device type | **Does not work today** | `require_tags` reads **device** tags, not DeviceType tags |

**Verdict:** Best **zero-touch + correct** option **without** plugin changes, if D2/D3 exist. Tag is an explicit “this object should have BMC template” signal — same family as `critical` / `snmp`.

---

## Option E — Manufacturer iDRAC + negative tag `no_idrac`

**How:** Keep Manufacturer assignment; tag exceptions to suppress.

| | |
|---|---|
| Plugin today | **Impossible** — no subtractive template inheritance |
| Would need | Plugin: exclude tag for templates, or “deny” assignments |

**Verdict:** Do not plan on this unless you invest in engine support. Prefer positive scoping (D/B).

---

## Option F — Gate on `oob_ip` only (transport as proxy for template)

**How:** Rely on empty `oob_ip` → no OOB SNMP IF → hope iDRAC does not link.

| | |
|---|---|
| Lab | Interface skipped; iDRAC could still show as eligible / retained |
| Storage with SNMP CG | Has SNMP IF on primary → iDRAC still links from Manufacturer |
| Verdict | Necessary for **where to poll**, insufficient for **whether iDRAC template applies** |

---

## Option G — Vendor-specific ConfigGroups

**How:** `Dell Server Agent+OOB` (Agent + OOB SNMP + iDRAC template on CG) vs `HPE Server Agent+OOB` (Agent + OOB SNMP + iLO). Assign by Manufacturer… but CG assignment is usually by Role — so need Manufacturer→CG (broken earlier: one effective CG, Manufacturer CG didn’t merge with Role) **or** Role+tag **or** DeviceType→CG.

| | |
|---|---|
| Scales | Multiplies CGs per vendor |
| Correctness | Good if assigned accurately |
| Complexity | High; fights “one Server BMC profile” |

**Verdict:** Only if you already need vendor-specific **transport**. Overkill for template scoping alone.

---

## Option H — Plugin enhancement (Manufacturer ∧ Role / `has_oob_ip`)

**How:** Extend TemplateRule (or assignment) with optional Manufacturer and/or `require_oob_ip=True`.

Example rule: platform `.*`, role `Server`, manufacturer Dell → iDRAC.

| | |
|---|---|
| Scales | Best long-term |
| Correctness | Exact |
| Cost | Upstream feature + tests + docs |
| Interim | Use D or B until it lands |

**Verdict:** Right permanent model; not required to unblock production if D or B ships first.

---

## Comparison

| Option | New Dell server auto? | Spares Dell storage? | Multi-vendor safe? | Plugin change? | Recommend |
|---|---|---|---|---|---|
| A Manufacturer | Yes | No | N/A | No | No (current pain) |
| B Device type list | If DT pre-seeded | Yes | Yes | No | **Yes — solid default** |
| C Role / BMC CG only | Yes | Yes (if storage≠Server) | **No** | No | No alone |
| D Tag + TemplateRule | If tag automation | Yes | Yes | No | **Yes — best zero-touch** |
| E Negative tag | Yes | If supported | Yes | **Yes** | Later maybe |
| F oob_ip only | Partial | No | Partial | No | Complement only |
| G Vendor CGs | Yes | Yes | Yes | No | Heavy |
| H Rule: Mfr∧Role | Yes | Yes | Yes | **Yes** | **Best end state** |

---

## Recommended path

### Current (plugin: Manufacturer on TemplateRule)

1. **Remove** Dell iDRAC from Manufacturer-wide template assignment.
2. Prefer **Option H**: TemplateRule  
   - `pattern`: `.*`  
   - `role_pattern`: `^Server$` (extend if other BMC roles should get iDRAC)  
   - `manufacturer`: Dell  
   - template: Dell iDRAC by SNMP  
3. Keep **Server Agent+OOB** for transport (`oob_ip`).
4. Keep OEM templates on **Device type**; they no longer fight Manufacturer iDRAC on storage.
5. Optional: tag-based rule (`require_tags=idrac`) only for exceptions; Device type list (**B**) as audit backup.

### Why not Manufacturer + hope Device type “overwrites”

Already disproved in lab: merge is additive; HP MSA + iDRAC both linked.

### Why Manufacturer ∧ Role (not tag-only)

- Uses facts already on the Device (manufacturer + role) — zero extra tagging for the happy path.
- Multi-vendor Server role stays safe (HPE Server does not get Dell iDRAC).
- Storage Dell devices fail the role criterion and never get iDRAC.
- Tag (`idrac`) remains available for overlays / exceptions.

### Interim without this field

**Option D** (role ∧ tag `idrac` + stamp automation) or **Option B** (Device type list) remain valid without the Manufacturer criterion.

---

## What we should not do

- Per-device iDRAC assignments as the mass pattern  
- Manufacturer iDRAC + “Device type overwrites” story  
- Role-only iDRAC on a multi-vendor Server role  
- Relying on empty `oob_ip` to mean “no iDRAC template”

---

## One-line recommendation

**Scope iDRAC by Manufacturer Dell ∧ role Server (TemplateRule); stop Manufacturer-wide iDRAC. Tags/Device types only as backup or exceptions.**
