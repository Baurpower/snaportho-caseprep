"""Claim-linked, topic-balanced evidence from the pinned packet, never rendered text."""
from collections import defaultdict, deque
import re

TOPICS = {
    'indications': 'approach_indication', 'relative_contraindications': 'approach_indication',
    'structures_at_risk': 'hazards', 'danger_zones': 'hazards',
    'retraction_hazards': 'hazards', 'complications': 'hazards', 'bailouts': 'hazards',
    'implant_implications': 'construct', 'fluoroscopy_implications': 'checks',
    'questions': 'questions',
}
REQUIRED_TOPICS = ('surgical_indication', 'exposure', 'hazards', 'postoperative')


def packet_evidence(packets, budget=60):
    groups = defaultdict(list)
    for packet in packets:
        graph = packet['_graph']
        claims = {c['claim_id']: c for c in packet['claims']}
        for field, values in packet.items():
            if field in {'claims', 'sources'} or not isinstance(values, list):
                continue
            for row in values:
                if not isinstance(row, dict):
                    continue
                text = row.get('text') or row.get('answer')
                ids = row.get('claim_ids') or []
                if not text or not ids or any(i not in claims for i in ids):
                    continue
                linked = [claims[i] for i in ids]
                refs = sorted({s for c in linked for s in c.get('source_ids', [])})
                if not refs:
                    continue
                topic = TOPICS.get(field, 'exposure')
                groups[topic].append({
                    'text': text, 'source_field': field, 'source_claim_ids': ids,
                    'source_ids': refs, 'approach_id': packet['approach_id'],
                    'packet_hash': graph['content_hash'], 'semantic_topic': topic,
                    'kind': 'approach_safety' if topic == 'hazards' else 'approach_exposure',
                    'qualifiers': graph['mappings'], 'effective_review_status': graph['approval'],
                    'risk_level': [c.get('risk_level') for c in linked],
                    'source_claims': linked,
                })
    queues = [deque(sorted(groups[t], key=lambda r: not any(v in ('critical','high') for v in r['risk_level'])))
              for t in ('hazards','exposure','checks','construct','approach_indication','questions') if groups[t]]
    result = []
    while queues and len(result) < budget:
        for queue in queues:
            if queue and len(result) < budget:
                result.append(dict(queue.popleft(), evidence_id=f'E{len(result)+1}'))
        queues = [q for q in queues if q]
    return result


def support_errors(output, evidence):
    """Fail closed: each assertion must be an exact supplied excerpt.

    This intentionally rejects paraphrase until an independently evaluated
    entailment system is deployed. Valid citation IDs alone cannot pass.
    """
    by_id = {r['evidence_id']: r for r in evidence}
    errors = []
    normalize = lambda s: re.sub(r'\s+', ' ', str(s)).strip().lower()
    for section in ('indications', 'critical_portion', 'postop_protocol'):
        for field, values in output.get(section, {}).items():
            if values is None or values == []:
                continue
            path = f'{section}.{field}'
            refs = output.get('citations', {}).get(path, [])
            rows = [by_id[r] for r in refs if r in by_id]
            expected = {'indications': {'surgical_indication'}, 'postop_protocol': {'postoperative'},
                        'critical_portion': {'exposure','hazards','checks','construct'}}[section]
            rows = [r for r in rows if r.get('semantic_topic') in expected]
            for value in values if isinstance(values, list) else [values]:
                if not any(normalize(value) == normalize(r['text']) for r in rows):
                    errors.append(f'unsupported assertion at {path}')
    return sorted(set(errors))
