# Approach Router + Safety Validation Test Results

Generated: 2026-06-06T01:00:50.899626+00:00

## Router-only tests
- bimalleolar ankle fracture ORIF: PASS family=ankle_fracture_orif
- trimalleolar ankle fracture ORIF with posterior malleolus: PASS family=ankle_fracture_orif
- distal radius fracture ORIF: PASS family=distal_radius_orif
- carpal tunnel release: PASS family=carpal_tunnel_release
- posterior THA: PASS family=posterior_tha
- anterior THA: PASS family=anterior_tha
- ambiguous ankle pain (no ORIF): PASS family=unknown

## End-to-end (router-aware GPT selector)
- bimalleolar ankle fracture ORIF: ERROR The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable
- trimalleolar ankle fracture ORIF with posterior malleolus: ERROR The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable
- distal radius fracture ORIF: ERROR The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable
- carpal tunnel release: ERROR The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable