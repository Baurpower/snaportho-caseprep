try:
    print("🚀 Running checkvector.py...")

    import json
    import uuid
    import os
    from pinecone import Pinecone
    from dotenv import load_dotenv
    from tqdm import tqdm

    # ── Load API Keys ──
    load_dotenv()
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX")

    if not api_key or not index_name:
        raise ValueError("Missing Pinecone API key or index name in .env file")

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    print(f"✅ Connected to index: {index_name}")

    # ── Settings ──
    input_path = "output_vectorversion_pp.jsonl"
    output_path = "to_upload.jsonl"
    BATCH_SIZE = 100

    # ── Load Local Records ──
    print(f"📂 Reading from: {input_path}")
    local_cards = []
    with open(input_path, "r") as f:
        for i, line in enumerate(f):
            card = json.loads(line)
            if "id" not in card:
                card["id"] = f"card-{uuid.uuid4().hex[:8]}"  # Assign random unique ID
            local_cards.append(card)

    all_ids = [card["id"] for card in local_cards]
    print(f"🔎 Loaded {len(all_ids)} IDs.")

    # ── Check for Existing IDs ──
    existing_ids = set()
    for i in tqdm(range(0, len(all_ids), BATCH_SIZE), desc="Checking Pinecone"):
        batch_ids = all_ids[i:i + BATCH_SIZE]
        try:
            res = index.fetch(ids=batch_ids)
            existing_ids.update(res.vectors.keys())
        except Exception as e:
            print(f"❌ Error fetching batch {i}-{i + BATCH_SIZE}: {e}")

    # ── Filter New Cards ──
    new_cards = [card for card in local_cards if card["id"] not in existing_ids]

    print(f"✅ Total cards in file: {len(local_cards)}")
    print(f"🟡 Already in index: {len(existing_ids)}")
    print(f"🆕 New cards to upload: {len(new_cards)}")

    # ── Save New Cards to Upload ──
    if new_cards:
        with open(output_path, "w") as f:
            for card in new_cards:
                f.write(json.dumps(card) + "\n")
        print(f"📁 Saved new cards to: {output_path}")
    else:
        print("🚫 No new cards to upload.")

except Exception as e:
    print(f"❌ Script error: {e}")
