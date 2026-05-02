#!/usr/bin/env python3
"""
Batch knowledge graph generator for all Taoist classics.

Scans chapters/ directory for .tagged.md files, extracts entities and co-occurrence
relations, and generates *_kg.json and *_kg.mmd files for each classic.

Usage:
  python3 scripts/generate_kg_batch.py
  python3 scripts/generate_kg_batch.py --only 抱朴子 黄帝阴符经
"""

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS_DIR = ROOT / "chapters"
TAG_RE = re.compile(r'〖@([^:]+):([^〗]+)〗')

# Color definitions for Mermaid
CLASS_DEFS = """classDef person fill:#f9f,stroke:#333,stroke-width:2px;
classDef place fill:#ccf,stroke:#333,stroke-width:2px;
classDef bio fill:#cfc,stroke:#333,stroke-width:2px;
classDef concept fill:#fcf,stroke:#333,stroke-width:2px;
classDef state fill:#ffc,stroke:#333,stroke-width:2px;
classDef metaphor fill:#cff,stroke:#333,stroke-width:2px;
classDef subject fill:#fdd,stroke:#333,stroke-width:2px;
classDef duality fill:#ddd,stroke:#333,stroke-width:2px;"""

TYPE_TO_CLASS = {
    "人物": "person",
    "地名": "place",
    "生物": "bio",
    "概念": "concept",
    "境界": "state",
    "隐喻": "metaphor",
    "意象": "metaphor",
    "主体": "subject",
    "对立": "duality",
}


def extract_tags(content: str) -> List[Tuple[str, str]]:
    return TAG_RE.findall(content)


def generate_kg_for_classic(classic_name: str, chapter_dir: Path) -> Dict:
    """
    Generate knowledge graph for a single classic.
    """
    nodes = {}  # { (type, name): count }
    edges = defaultdict(int)  # { ((t1, n1), (t2, n2)): count }
    file_entities = {}  # { filename: set of (type, name) }
    total_files = 0
    total_tags = 0

    tagged_files = sorted(chapter_dir.glob("*.tagged.md"))
    total_files = len(tagged_files)

    if total_files == 0:
        return {"status": "skip", "reason": "no .tagged.md files found"}

    for filepath in tagged_files:
        content = filepath.read_text(encoding="utf-8")
        tags = extract_tags(content)
        total_tags += len(tags)

        entities = set()
        for t_type, name in tags:
            node_key = (t_type, name.strip())
            nodes[node_key] = nodes.get(node_key, 0) + 1
            entities.add(node_key)

        file_entities[filepath.name] = entities

        # Co-occurrence edges within same file
        ent_list = list(entities)
        for i in range(len(ent_list)):
            for j in range(i + 1, len(ent_list)):
                pair = tuple(sorted([ent_list[i], ent_list[j]]))
                edges[pair] += 1

    # Build JSON output
    kg_data = {
        "metadata": {
            "classic": classic_name,
            "total_chapters": total_files,
            "total_tags": total_tags,
            "unique_entities": len(nodes),
        },
        "nodes": [
            {"id": f"{t}:{n}", "type": t, "name": n, "weight": count}
            for (t, n), count in sorted(nodes.items(), key=lambda x: x[1], reverse=True)
        ],
        "links": [
            {
                "source": f"{p[0][0]}:{p[0][1]}",
                "target": f"{p[1][0]}:{p[1][1]}",
                "weight": count,
            }
            for p, count in sorted(edges.items(), key=lambda x: x[1], reverse=True)
            if count > 1  # Only strong links
        ],
    }

    # Write JSON
    json_path = ROOT / f"{classic_name}_kg.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(kg_data, f, ensure_ascii=False, indent=2)

    # Generate Mermaid (top 40 nodes by weight)
    top_nodes = sorted(nodes.items(), key=lambda x: x[1], reverse=True)[:40]
    top_node_ids = {f"{t}:{n}" for (t, n), count in top_nodes}

    mermaid = "graph LR\n"
    mermaid += CLASS_DEFS + "\n"

    for (t, n), count in top_nodes:
        node_id = f"{t}_{n}".replace(" ", "_").replace("(", "").replace(")", "").replace(":", "_")
        mermaid += f"  {node_id}({n})\n"
        if t in TYPE_TO_CLASS:
            mermaid += f"  class {node_id} {TYPE_TO_CLASS[t]};\n"

    # Add edges between top nodes
    for (p1, p2), count in edges.items():
        id1 = f"{p1[0]}:{p1[1]}"
        id2 = f"{p2[0]}:{p2[1]}"
        if id1 in top_node_ids and id2 in top_node_ids and count > 2:
            m_id1 = id1.replace(":", "_").replace(" ", "_").replace("(", "").replace(")", "")
            m_id2 = id2.replace(":", "_").replace(" ", "_").replace("(", "").replace(")", "")
            mermaid += f"  {m_id1} --- {m_id2}\n"

    mmd_path = ROOT / f"{classic_name}_kg.mmd"
    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid)

    return {
        "status": "done",
        "chapters": total_files,
        "tags": total_tags,
        "entities": len(nodes),
        "links": len(kg_data["links"]),
        "json": str(json_path.relative_to(ROOT)),
        "mmd": str(mmd_path.relative_to(ROOT)),
    }


def run(selected: List[str]) -> None:
    """
    Process all classics in chapters/ directory.
    """
    selected_set = set(selected)
    results = []

    # Discover classic directories
    for entry in sorted(CHAPTERS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if selected_set and entry.name not in selected_set:
            continue

        print(f"Processing: {entry.name}")
        result = generate_kg_for_classic(entry.name, entry)
        results.append({"name": entry.name, **result})

        if result["status"] == "skip":
            print(f"  [SKIP] {result['reason']}")
        else:
            print(f"  [OK] {result['chapters']} chapters, {result['tags']} tags, {result['entities']} entities, {result['links']} links")
            print(f"  JSON: {result['json']}")
            print(f"  MMD:  {result['mmd']}")
        print()

    # Summary
    print("=" * 50)
    print("Summary:")
    done = [r for r in results if r["status"] == "done"]
    skipped = [r for r in results if r["status"] == "skip"]
    print(f"  Processed: {len(done)}")
    print(f"  Skipped: {len(skipped)}")
    if skipped:
        for r in skipped:
            print(f"    - {r['name']}: {r['reason']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch generate knowledge graphs for Taoist classics")
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Only process specified classics, e.g. --only 抱朴子 黄帝阴符经",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.only)
