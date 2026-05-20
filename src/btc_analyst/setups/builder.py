from __future__ import annotations

import json
import time


def build_setup(zone, entry, stop, t1, t2, reaction, trigger):
    risk = abs(entry - stop)
    rr1 = abs(t1 - entry) / risk if risk else 0
    rr2 = abs(t2 - entry) / risk if (risk and t2 is not None) else None
    return {
        'zone_id': zone['id'],
        'direction': 'long' if zone['zone_type'] == 'support' else 'short',
        'entry_price': float(entry),
        'stop_price': float(stop),
        'target1_price': float(t1),
        'target2_price': float(t2) if t2 is not None else None,
        'rr_to_t1': float(rr1),
        'rr_to_t2': float(rr2) if rr2 is not None else None,
        'reaction_type': reaction,
        'trigger_type': trigger,
        'confidence': float(zone.get('score', 0)),
        'status': 'active',
        'notes_json': json.dumps({}),
        'tier': str(zone.get('setup_tier', 'legacy')),
        'risk_multiplier': float(zone.get('risk_multiplier', 1.0)),
    }


def persist_setup(conn, setup: dict) -> int:
    cur = conn.execute(
        """INSERT INTO setups(
            created_at,zone_id,direction,entry_price,stop_price,target1_price,target2_price,
            rr_to_t1,rr_to_t2,confidence,reaction_type,trigger_type,status,notes_json,tier,risk_multiplier
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            int(time.time()),
            setup['zone_id'],
            setup['direction'],
            setup['entry_price'],
            setup['stop_price'],
            setup['target1_price'],
            setup.get('target2_price'),
            setup['rr_to_t1'],
            setup.get('rr_to_t2'),
            setup['confidence'],
            setup['reaction_type'],
            setup['trigger_type'],
            setup.get('status', 'active'),
            setup.get('notes_json', '{}'),
            setup.get('tier', 'legacy'),
            setup.get('risk_multiplier', 1.0),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)
