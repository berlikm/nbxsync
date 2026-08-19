# Port-label compliance — how to run it, how to read it

Audience: network engineers using NetBox 4.5. The script is a **Custom Script**,
not a plugin and not a Report (Reports were folded into Scripts in NetBox 4.x).
That is the ceiling: a job log + a CSV in the Output tab + a red/green job.
This note is the operations playbook for that ceiling.

Grammar: [`port-identity-foundation.md`](../reference/port-identity-foundation.md).
Generator + CLI: [`README-extreme-port-labels.md`](README-extreme-port-labels.md).

---

## 1. What you should open first (no NetBox required)

The generator was replayed against every cabled Extreme port we have in the
fleet canary (**1535** ports, **328** devices, **17** sites):

| File | What it is |
|---|---|
| [`port-label-preview.md`](port-label-preview.md) | Counts + the rows worth eyeballing (ISC, stack, 20-char, concat) |
| [`fixtures/port_label_preview.tsv`](fixtures/port_label_preview.tsv) | Full sheet — open in Excel, filter |

This is **plan-only**: NetBox cabling → expected `ifAlias`. It is not a live
vs expected diff. Live comparison needs a **Compliance** run against the box.

Sanity on that sheet today:

- 0 labels contain a `.`
- 0 duplicate labels on the same device
- 0 labels over 20 characters
- ISC (42) and stack (56) are **`USW`**, not `X`
- CLASS mix: USW 1036 · UP 243 · US 186 · MON 70

If Preview in NetBox and this TSV disagree, cabling changed since the export —
trust Preview, then refresh the canary.

---

## 2. How a network engineer should use NetBox

Three modes, same script. **Do them in this order.**

| Step | Mode | SSH? | Commit? | What you get |
|---|---|---|---|---|
| 1 | **Preview** (default) | no | no | Expected labels from cabling. Per-device scorecard + CSV |
| 2 | **Compliance** | read | no | Live vs expected. Blocking table + CSV. No push |
| 3 | **Remediate** | write | **yes** + allowlist | Push. First run: **one device, few ports** |

### 2.1 How to read the job (NetBox 4.5)

1. **Log — scorecard.** Status counts, CLASS mix, blocking / hijacked /
   collision totals, then **one line per switch** (`ok`, `blocking`, `diff`,
   `miss`, `hijack`, `kept`, `unreach`, `coll`, `long`). Blocking tables are
   capped at 40 rows. This is for scanning, not for 1500 diffs.
2. **Output — CSV.** Every evaluated port. Copy → Excel. This is the sheet you
   keep. First line is `sep=,` (Excel delimiter) plus a UTF-8 BOM. VOSS
   `1/17` is a text formula so Excel does not make it a date.
3. Do **not** treat the job log as the archive. NetBox truncates long logs.

`ok` means **Zabbix ifAlias matches expected**. It is not “display-string
matches.” On EXOS, a leftover `description-string` still wins ifAlias; that
row is `alias_hijacked` and **blocking** until you tick clear.

### 2.2 Excel filters

| Filter | Why |
|---|---|
| `blocking = yes` | The work queue. Diff + missing + too_long + forbidden + unreachable + alias_hijacked + collision |
| `status = diff` | Box display-string / VOSS `name` ≠ cabling |
| `status = missing` | Cabled in NetBox, no live label |
| `status = alias_hijacked` | Grammar is on display-string; Zabbix still reads description-string |
| `status = unreachable` | SSH failed or no `oob_ip`/`primary_ip`. The job **always fails** — we cannot attest those ports |
| `collision = yes` | Two ports on this switch share `expected` (not `X`/`N`) |
| `status = kept` | Label on the box, no complete cable. **Listed, never wiped.** Often still useful (ISP, leftover NIC) |
| `collision = yes` | Two ports on this switch share `expected`. Generator cannot pick a winner |
| `class` | `USW` / `US` / `UP` / `MON` / `UW` / `X` — own column, do not parse `expected` |
| `ifalias_source = description-string` | Zabbix is not looking at display-string |
| `far_role` contains Core / Dist | Fabric |
| `len = 20` | At the EXOS budget; check it still reads |

### 2.3 First live run

Scope the first live compliance to **one EXOS and one VOSS**. Canary allowlist
is `device-name::ifname` per line (copy ifName from NetBox, not from the CLI —
VOSS `1/17` vs `1:17` will miss). Do not start with “all sites”.

Permissions (NetBox Object Permissions, not the script):

- **Preview / compliance:** `extras.run_script` is enough. The script does not
  write NetBox objects.
- **Remediate:** same permission **plus** the Commit box. NetBox has no
  per-mode permission — that is why remediate is double-gated (mode + Commit +
  allowlist or an explicit “entire scope” tick).
- Do **not** grant `run_script` to everyone. Custom scripts can SSH with the
  NAPALM credentials.

Scheduled compliance: tick **Fail the job on blocking label diffs**. Unreachable
boxes fail the job even without that tick. Hook a NetBox event rule on failed
script jobs if you want mail/Slack. Leave the diffs tick off for the first
interactive fleet run (everything will be `diff`).

---

## 3. Options we considered (and what we actually use)

| Option | Verdict |
|---|---|
| **Custom Script + scorecard log + CSV Output** | **Use this.** Native NetBox 4.5. No plugin. Output tab is copy-paste into Excel. |
| Markdown-only job log | Too small. NetBox truncates; 1535 rows is unreadable. Log = scorecard + 40 blocking rows. |
| Custom Report | Dead in 4.x. Scripts replaced Reports. |
| Custom field on Interface (`expected_label`) | Duplicates cabling; goes stale when someone moves a cable. |
| Writing the grammar into NetBox `Interface.label` / description | **No.** XIQ-SE already maps `display-string` → interface data. Write-back loop. |
| Export template (Jinja) | Duplicate of the generator, cannot reuse the Python ladder, cannot SSH. |
| Plugin with a table view | Better UX, extra install/upgrade surface. Same generator. Not needed to ship labels. |
| Saving CSV under `/media` | Needs disk + cleanup. Output-tab CSV is enough. |
| GraphQL / REST + a laptop script | Fine for us; not for the NOC. Keep the button in NetBox. |

**Best practice:** cabling in NetBox is the source of truth; the on-box
`ifAlias` is the copy Zabbix reads; the script is the **diff** between those
two. Nothing else stores the expected string.

---

## 4. Code / security review (senior, network-aware)

The script is the right shape for NetBox: a **flat file** next to
`extreme_cli_runner.py`, no secrets in git, SSH via the existing runner,
`commit_default = False`.

### What is already sound

- Credentials from env (`NBX_NAPALM_*`), never from the form.
- OOB IP first, then primary. It does not invent an address.
- Remediate is off unless **mode + Commit**. Preview never opens SSH.
- Uncabled live labels are `kept` and **never** pushed.
- EXOS `description-string` is not cleared unless that box is ticked.
- A matching display-string with a leftover description-string is
  `alias_hijacked`, not `ok`.
- Unreachable boxes **always** fail the job (`log_failure` + `obj=device`).
  Label diffs fail only when **Fail the job on blocking label diffs** is ticked.
- Duplicate expected labels on one switch are `collision=yes` (blocking).
  Multiple `X` (SPAN) ports on the same switch are **not** collisions.
- Device names in the scorecard are NetBox links (`/dcim/devices/<id>/`).
- Fleet-wide scope is Extreme manufacturer **or** EXOS/VOSS/Switch Engine /
  Fabric Engine platform — it does not scan every server in DCIM.
- Canary allowlist treats `1:17` and `1/17` as the same port.
- Label length and charset are checked again immediately before the write.
- Threads call `close_old_connections()` so Django is not surprised.

### Residual (accept, do not “fix” into something worse)

- NetBox Custom Scripts are **full Python** in the NetBox process. Anyone who
  can add a script can take the NAPALM env. Limit `extras.add_scriptmodule`.
- Auto-confirm `y/N` is the runner’s behaviour (needed for `save`). Display-string
  itself does not prompt.
- Canary allowlist is `device::ifName`. `1:17` and `1/17` match. Copy the
  device name from NetBox.
- If `oob_ip` is empty, SSH goes to `primary_ip` (in-band). Fill OOB in NetBox.
- Live `show running-config` on VOSS can be slow; timeout is 180s.
- `mgmt` / `oob` as substrings on a far-port name can false-positive BMC.
  Prefer `oob_ip` assigned to that interface and `mgmt_only`.

### What we deliberately did **not** do

- Do not store passwords in NetBox secrets *and* env — one store (env, same as
  the firmware script).
- Do not parse `connected_endpoints` into a recursive cable walker here; NetBox
  already walks patch-panel front/rear. Incomplete paths stay `kept`.
- Do not auto-`X` ISC from the description. That was the monitoring bug.
- Do not dump 1500 diffs into the job log. CSV is the archive.

---

## 5. First live run (checklist)

1. Copy `extreme_port_labels.py` next to `extreme_cli_runner.py` in `SCRIPTS_ROOT`.
2. NetBox → Customization → Scripts → **Extreme Port Labels**.
3. Mode **Preview**, pick **Scope** (one site or a few devices). Leave canary empty — it is ignored. **No Commit**. Copy CSV from Output.
4. Eyeball ISC / stack / SAN / AP rows. Floor tokens (`GFL`, `L02`) must still
   be there on 1G uplinks. `collision=yes` must be empty.
5. Mode **Compliance** on **one EXOS** and **one VOSS**. Confirm live parse
   (display-string vs `name`). Confirm `alias_hijacked` if description-string
   is set.
6. Mode **Remediate**, Commit ticked, canary allowlist = those few
   `device::ifname` lines. If Zabbix still shows the old string, the port was
   hijacked — tick clear on a second pass.
7. Confirm `ifAlias` in Zabbix after the next LLD. Only then widen scope.
