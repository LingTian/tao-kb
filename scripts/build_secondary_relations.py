#!/usr/bin/env python3
"""
Build second-layer relations from tagged chapters.

Output:
  - relations/secondary_relations.json
"""

import json
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS_DIR = ROOT / "chapters"
OUT_FILE = ROOT / "relations" / "secondary_relations.json"

TAG_RE = re.compile(r"〖@([^:]+):([^〗]+)〗")
SENTENCE_SPLIT_RE = re.compile(r"[。！？；\n]+")


def iter_tagged_files() -> List[Path]:
    files = []
    for path in CHAPTERS_DIR.rglob("*.tagged.md"):
        if "legacy" in path.parts:
            continue
        files.append(path)
    return sorted(files, key=lambda p: str(p).lower())


def normalize_entity(tag_type: str, name: str) -> str:
    return f"{tag_type}:{name.strip()}"


def extract_sentence_relations(sentence: str, chapter: str, sent_idx: int) -> List[Dict]:
    tags = [(m.group(1).strip(), m.group(2).strip()) for m in TAG_RE.finditer(sentence)]
    entities = [normalize_entity(t, n) for t, n in tags]
    relations: List[Dict] = []

    # 1) Explicit contrast from 对立:a|b
    for t, n in tags:
        if t == "对立" and "|" in n:
            left, right = [x.strip() for x in n.split("|", 1)]
            if left and right:
                relations.append(
                    {
                        "relation": "contrast",
                        "source": f"概念:{left}",
                        "target": f"概念:{right}",
                        "evidence": sentence.strip()[:120],
                        "chapter": chapter,
                        "sentence_index": sent_idx,
                        "confidence": 0.95,
                        "method": "rule:duality_tag",
                    }
                )

    # 2) Causal hint (sentence-level weak relation)
    if len(entities) >= 2 and any(k in sentence for k in ("故", "所以", "则", "因", "是以")):
        relations.append(
            {
                "relation": "causal_hint",
                "source": entities[0],
                "target": entities[-1],
                "evidence": sentence.strip()[:120],
                "chapter": chapter,
                "sentence_index": sent_idx,
                "confidence": 0.6,
                "method": "rule:causal_keyword",
            }
        )

    # 3) Progression hint
    if len(entities) >= 2 and any(k in sentence for k in ("而后", "然后", "乃", "遂")):
        relations.append(
            {
                "relation": "progression_hint",
                "source": entities[0],
                "target": entities[-1],
                "evidence": sentence.strip()[:120],
                "chapter": chapter,
                "sentence_index": sent_idx,
                "confidence": 0.55,
                "method": "rule:progression_keyword",
            }
        )

    # 4) Co-occurrence pairs
    uniq = sorted(set(entities))
    for a, b in combinations(uniq, 2):
        relations.append(
            {
                "relation": "co_occurs",
                "source": a,
                "target": b,
                "evidence": sentence.strip()[:120],
                "chapter": chapter,
                "sentence_index": sent_idx,
                "confidence": 0.4,
                "method": "rule:sentence_cooccurrence",
            }
        )
    return relations


def build_relations() -> Dict:
    all_relations: List[Dict] = []
    chapter_counts: Dict[str, int] = {}

    for path in iter_tagged_files():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        sentences = [s for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
        count_before = len(all_relations)
        for i, sent in enumerate(sentences, start=1):
            all_relations.extend(extract_sentence_relations(sent, rel, i))
        chapter_counts[rel] = len(all_relations) - count_before

    # aggregate summary
    relation_type_counts = defaultdict(int)
    for r in all_relations:
        relation_type_counts[r["relation"]] += 1

    return {
        "metadata": {
            "project": "tao-kb",
            "description": "Second-layer relation annotations generated from tagged chapters",
            "source_glob": "chapters/**/*.tagged.md (excluding legacy)",
        },
        "stats": {
            "total_chapters": len(chapter_counts),
            "total_relations": len(all_relations),
            "relation_type_counts": dict(sorted(relation_type_counts.items())),
        },
        "chapter_relation_counts": chapter_counts,
        "relations": all_relations,
    }


def main() -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = build_relations()
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated second-layer relations -> {OUT_FILE}")
    print(f"Total relations: {data['stats']['total_relations']}")
    print(f"By type: {data['stats']['relation_type_counts']}")


if __name__ == "__main__":
    main()
