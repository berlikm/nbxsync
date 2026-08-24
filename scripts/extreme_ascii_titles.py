"""Keep Zabbix problem titles ASCII.

``≠`` in trigger ``event_name`` shows as ``Γëá`` (UTF-8 read as CP437) in
tickets and some Problems views. YAML already uses ``!=``; ``--apply`` still
has to patch live prototypes because configuration.import can leave the old
glyph, and LLD copies ``event_name`` onto discovered triggers.

Open PROBLEM rows keep the title from create. This module does not close or
re-fire them (that would bounce tickets). They pick up ``!=`` after recover.
"""

from __future__ import annotations

# UTF-8 U+2260 (≠) as CP437: E2 89 A0 → Γ ë á
_MOJIBAKE_NE = 'Γëá'

_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ('\u2260', '!='),  # ≠
    ('\u2264', '<='),  # ≤
    ('\u2265', '>='),  # ≥
    ('\u2014', '-'),   # em dash
    ('\u2013', '-'),   # en dash
    ('\u00a0', ' '),   # nbsp
    (_MOJIBAKE_NE, '!='),
)

def ascii_zabbix_title(text: str) -> str:
    """Replace Unicode operators / dashes that break problem titles."""
    out = text or ''
    for src, dst in _REPLACEMENTS:
        if src in out:
            out = out.replace(src, dst)
    return out


def title_needs_ascii(text: str) -> bool:
    return ascii_zabbix_title(text) != (text or '')


def title_payload(row: dict) -> dict:
    """Zabbix trigger / triggerprototype.update fields that still have glyphs."""
    payload: dict[str, str] = {}
    event = str(row.get('event_name') or '')
    new_event = ascii_zabbix_title(event)
    if new_event != event:
        payload['event_name'] = new_event
    # API name; ignore YAML ``name`` here (not an update field).
    name = str(row.get('description') or '')
    new_name = ascii_zabbix_title(name)
    if new_name != name:
        payload['description'] = new_name
    return payload


def yaml_title_fields_needing_ascii(trigger: dict) -> list[str]:
    """Return ``field=value`` for YAML trigger name / event_name / opdata."""
    bad: list[str] = []
    for field in ('name', 'event_name', 'opdata'):
        val = str(trigger.get(field) or '')
        if val and title_needs_ascii(val):
            bad.append(f'{field}={val}')
    return bad
