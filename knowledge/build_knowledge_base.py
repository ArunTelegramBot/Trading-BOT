"""Build a compact Hermes knowledge base from one or more study-note text files."""
import argparse
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

SEP = re.compile(r"^={5,}\s*$")
RULE_WORDS = re.compile(r"\b(should|must|avoid|never|do not|don't|prefer|use|buy|sell|entry|exit|stop|risk|diversif|momentum|reversion|trend|volume|drawdown|position size|valuation|cost|fee|tax)\b", re.I)
CONCEPTS = ["trend", "momentum", "mean reversion", "volume", "volatility", "risk", "drawdown", "position sizing", "stop loss", "take profit", "diversification", "valuation", "fundamental", "technical", "behavior", "cost", "liquidity", "index", "factor"]

def clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def section_title(block: str, number: int) -> str:
    lines = [x.strip() for x in block.splitlines() if x.strip()]
    for line in lines[:8]:
        if len(line) <= 140 and not line.isupper() or line.isupper() and len(line.split()) <= 14:
            return line
    return f"Section {number}"

def keywords(text: str) -> list[str]:
    low = text.lower()
    return [c for c in CONCEPTS if c in low]

def split_chunks(text: str, max_chars: int = 1800, overlap: int = 220) -> list[str]:
    paragraphs = [clean(p) for p in re.split(r"\n\s*\n", text) if clean(p)]
    chunks, current = [], ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            tail = current[-overlap:] if current else ""
            current = f"{tail}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks

def build(source_paths: list[Path], output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks, rules, concept_counts = [], [], Counter()
    for source_path in source_paths:
        raw = source_path.read_text(errors="replace")
        blocks = []
        current = []
        for line in raw.splitlines():
            if SEP.match(line):
                if current:
                    blocks.append("\n".join(current)); current = []
            else:
                current.append(line)
        if current:
            blocks.append("\n".join(current))
        for section_no, block in enumerate(blocks, start=1):
            title = section_title(block, section_no)
            for chunk_no, text in enumerate(split_chunks(block), start=1):
                cid = f"{source_path.stem[:24]}-s{section_no:03d}-c{chunk_no:03d}"
                tags = keywords(text)
                concept_counts.update(tags)
                record = {"chunk_id": cid, "source_file": source_path.name, "section": title, "section_number": section_no, "chunk_number": chunk_no, "tags": tags, "text": text}
                chunks.append(record)
                if RULE_WORDS.search(text):
                    rules.append({"rule_id": f"rule-{len(rules)+1:05d}", "source_chunk_id": cid, "source_file": source_path.name, "section": title, "pattern": tags, "rule_text": text, "confidence": "candidate_for_testing", "status": "research_only"})
    (output_dir / "knowledge_chunks.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in chunks) + "\n")
    (output_dir / "rule_cards.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rules) + "\n")
    (output_dir / "concepts.json").write_text(json.dumps({"concept_counts": concept_counts, "chunk_count": len(chunks), "rule_candidate_count": len(rules)}, indent=2))
    db = sqlite3.connect(output_dir / "knowledge_index.sqlite")
    db.execute("DROP TABLE IF EXISTS chunks")
    db.execute("DROP TABLE IF EXISTS chunks_fts")
    db.execute("CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, source_file TEXT, section TEXT, tags TEXT, text TEXT)")
    db.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_id UNINDEXED, source_file, section, tags, text)")
    for item in chunks:
        values = (item["chunk_id"], item["source_file"], item["section"], " ".join(item["tags"]), item["text"])
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?)", values)
        db.execute("INSERT INTO chunks_fts VALUES (?,?,?,?,?)", values)
    db.commit(); db.close()
    print(json.dumps({"chunks": len(chunks), "rule_candidates": len(rules), "concepts": concept_counts}, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/knowledge"))
    args = parser.parse_args()
    build(args.sources, args.output)
