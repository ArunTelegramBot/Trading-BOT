"""Low-token retrieval for Hermes. Returns only the most relevant knowledge chunks."""
import json
import sqlite3
from pathlib import Path

def retrieve(query: str, index_path: str = "data/knowledge/knowledge_index.sqlite", limit: int = 8) -> list[dict]:
    db = sqlite3.connect(index_path)
    terms = " OR ".join(x for x in query.replace('"', ' ').split() if x)
    rows = db.execute("SELECT chunk_id, source_file, section, tags, text FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?", (terms, limit)).fetchall()
    db.close()
    return [{"chunk_id": r[0], "source_file": r[1], "section": r[2], "tags": r[3].split(), "text": r[4]} for r in rows]

def hermes_context(query: str, index_path: str = "data/knowledge/knowledge_index.sqlite", limit: int = 8) -> str:
    records = retrieve(query, index_path, limit)
    return json.dumps({"query": query, "retrieved_knowledge": records, "instruction": "Use this as research input only. Propose, test, and request approval; do not send live orders."}, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import sys
    print(hermes_context(" ".join(sys.argv[1:]) or "risk trend volume"))
