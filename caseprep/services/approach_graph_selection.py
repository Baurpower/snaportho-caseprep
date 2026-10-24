"""Conservative choice construction using only this request's approved candidates."""
from copy import deepcopy
import re


def normalized(value):
    return ' '.join(re.findall(r'[a-z0-9]+', str(value).lower()))


def select_graph_approach(prompt, response):
    query = f' {normalized(prompt)} '
    candidates = []
    excluded = []
    for row in response.get('candidates', []):
        packet = row['packet']
        mappings = row['mappings']
        # Old aliases explicitly identified as needing review are not serving permissions.
        if not mappings or not any(m.get('mapping_status') in {'authored_packet','procedure_id_alias','authored_v3_agent_review_pending'} for m in mappings):
            excluded.append(row['approach_id'])
            continue
        label = normalized(' '.join([packet.get('name', ''), row['approach_id']]))
        incompatible = any(a in query and b in label and a not in label for a,b in (
            ('retrograde','antegrade'),('antegrade','retrograde'),
            ('adult','pediatric'),('pediatric','adult'),
            ('closed','open'),('percutaneous','open'),
        ))
        if 'periprosthetic' in label and 'periprosthetic' not in query and 'periprosthetic' not in response.get('procedure_slug', ''):
            incompatible = True
        if incompatible:
            excluded.append(row['approach_id'])
            continue
        candidates.append(row)
    options = [{
        'approach_id': r['approach_id'], 'name': r['packet'].get('name', r['approach_id']),
        'aliases': r['packet'].get('aliases', []), 'role': 'applicable',
        'selection_indications': [m.get('condition','') for m in r['mappings'] if m.get('condition')],
        'selection_limitations': [], 'content_status': r['packet'].get('content_status'),
        'review_status': 'approved', 'content_hash': r['content_hash'],
    } for r in candidates]
    matches = []
    for r in candidates:
        p = r['packet']
        phrases = [r['approach_id'], p.get('name', ''), *p.get('aliases', [])]
        if any(normalized(s) and f' {normalized(s)} ' in query for s in phrases):
            matches.append(r)
    # A unique approach id must not discard another packet that matches the same named phrase.
    if any(word in query for word in (" without ", " avoid ", " not ", " versus ", " vs ")):
        matches = []
    # No implicit first-row/default selection, even when only one option exists.
    selected = matches[0] if len(matches) == 1 else None
    decision = {
        'approaches': options, 'selected_approach_id': selected['approach_id'] if selected else None,
        'selected_approach_ids': [selected['approach_id']] if selected else [],
        'status': 'selected' if selected else ('choice_required' if options else 'unavailable'),
        'message': 'Confirm the approach and its listed applicability conditions.' if not selected else 'Explicit approach selected.',
        'selection_reason': 'explicit_exact_match' if selected else ('ambiguous_or_unspecified' if options else 'no_eligible_mapping'),
        'excluded_approach_ids': excluded,
    }
    packets = []
    if selected:
        packet = deepcopy(selected['packet'])
        packet['_graph'] = {k: deepcopy(v) for k,v in selected.items() if k != 'packet'}
        packets.append(packet)
    return decision, packets
