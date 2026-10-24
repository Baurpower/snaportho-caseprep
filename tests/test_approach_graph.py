import asyncio
import hashlib
import json
from copy import deepcopy

import httpx
import pytest

from caseprep.services.approach_graph_provider import ApproachGraphProvider, GraphResponse
from caseprep.services.approach_graph_selection import select_graph_approach
from caseprep.services.approach_graph_evidence import packet_evidence, support_errors
from caseprep.pipelines.approach_prep import build_approach_prep
from caseprep.services.essentials_v1_3 import generate_essentials


def fixture():
    p = {'approach_id': 'modified_henry', 'name': 'Modified Henry', 'aliases': [],
         'claims': [{'claim_id':'c1','source_ids':['s1'],'text':'Protect the nerve.','risk_level':'high'}],
         'sources':[{'source_id':'s1','url':'https://example.org'}],
         'danger_zones':[{'text':'Protect the nerve.','claim_ids':['c1']}],
         'indications':[{'text':'Use this corridor.','claim_ids':['c1']}]}
    h = hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    return {'procedure_slug':'distal_radius', 'status':'available','candidates':[{
        'approach_id':p['approach_id'],'canonical_entity_id':'00000000-0000-0000-0000-000000000001',
        'procedure_entity_id':'00000000-0000-0000-0000-000000000002',
        'content_hash':h,'packet':p,'mappings':[{'mapping_status':'authored_packet','condition':'Volar exposure'}],
        'approval':{'status':'approved','revoked':False,'approving_party':'user','basis':'attestation','approved_at':'2026-10-24T00:00:00Z'}}]}


def test_contract_hash_and_approval():
    GraphResponse.model_validate(fixture())
    for mutate in (lambda r:r['candidates'][0]['packet'].update(name='changed'),
                   lambda r:r['candidates'][0]['approval'].update(revoked=True),
                   lambda r:r.update(status='no_mapping')):
        r=fixture(); mutate(r)
        with pytest.raises(ValueError): GraphResponse.model_validate(r)


def test_explicit_selection_pins_evidence():
    r=fixture()
    result=build_approach_prep('distal radius modified Henry','distal_radius',None,graph_response=r)
    assert result['coverage']['approach_id']=='modified_henry'
    r['candidates'][0]['packet']['danger_zones'][0]['text']='mutated'
    evidence=packet_evidence(result['selected_packets'])
    assert evidence[0]['text']=='Protect the nerve.'
    assert evidence[0]['source_claim_ids']==['c1']
    assert evidence[0]['packet_hash']==result['coverage']['packet_hash']
    brief=generate_essentials(identity={'canonical_name':'Distal radius'},payload=None,approach_prep=result,openai_client=None,model='unused')
    assert not brief['payload']['verification']['passed']
    assert 'surgical_indication' in brief['payload']['verification']['required_topic_gaps']
    assert brief['payload']['verification']['used_claim_ids']==['c1']


def test_no_arbitrary_selection_or_local_fallback():
    r=fixture()
    assert select_graph_approach('distal radius',r)[0]['status']=='choice_required'
    r['candidates'][0]['mappings'][0]['mapping_status']='legacy_review_required'
    assert not select_graph_approach('modified Henry',r)[1]
    assert not build_approach_prep('posterior THA','tha_posterior',{},graph_response={'status':'unavailable','candidates':[]})['sections']


def test_ambiguous_explicit_choices():
    r=fixture(); row=deepcopy(r['candidates'][0]);row['approach_id']='other';row['packet']['approach_id']='other'
    r['candidates'].append(row)
    assert select_graph_approach('modified Henry',r)[0]['status']=='choice_required'


def test_no_unrelated_numbers_contradictions_or_partial_lists():
    evidence=[{'evidence_id':'E1','text':'Protect the nerve.','semantic_topic':'hazards'}]
    for value in ('Cut the nerve.','Protect the nerve for 5 minutes.', ['Protect the nerve.','Cut the artery.']):
        assert support_errors({'critical_portion':{'summary':value},'citations':{'critical_portion.summary':['E1']}},evidence)
    assert not support_errors({'critical_portion':{'summary':'Protect the nerve.'},'citations':{'critical_portion.summary':['E1']}},evidence)
    assert support_errors({'indications':{'summary':'Protect the nerve.'},'citations':{'indications.summary':['E1']}},evidence)


@pytest.mark.parametrize('kind', ['ok','scope','auth','timeout','malformed','cancel'])
def test_provider(kind):
    async def run():
        calls=[]
        async def handler(request):
            calls.append(request)
            if kind=='timeout': raise httpx.ReadTimeout('sensitive secret')
            if kind=='cancel': raise asyncio.CancelledError()
            data=fixture()
            if kind=='scope': data['procedure_slug']='other'
            if kind=='malformed': data={'bad':'payload'}
            return httpx.Response(401 if kind=='auth' else 200,json=data)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            p=ApproachGraphProvider('https://example.org','secret',client=client)
            if kind=='cancel':
                with pytest.raises(asyncio.CancelledError): await p.fetch('distal_radius')
                return
            result=await p.fetch('distal_radius')
            assert len(calls)==1
            assert result['status']==('available' if kind=='ok' else 'unavailable')
            assert 'secret' not in json.dumps(result)
    asyncio.run(run())
