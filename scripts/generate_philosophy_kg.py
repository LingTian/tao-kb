#!/usr/bin/env python3
"""
Generate a combined knowledge graph for four philosophy classics:
- Dao De Jing
- Zhuang Zi
- Lie Zi
- Wen Zi
"""

import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
OUT_KG = ROOT / "philosophy_kg.json"
OUT_REPORT = ROOT / "philosophy_kg_report.json"
TAG_RE = re.compile(r"〖@([^:]+):([^〗]+)〗")


def target_files(debiased: bool = False) -> List[Tuple[str, Path]]:
    files: List[Tuple[str, Path]] = []
    # Dao De Jing
    for p in sorted((ROOT / "chapters").glob("daodejing_*.tagged.md")):
        files.append(("Dao De Jing(道德经)", p))
    # Zhuang Zi
    for p in sorted((ROOT / "chapters" / "zhuangzi").glob("*.tagged.md")):
        if "legacy" in p.parts:
            continue
        if debiased and p.name.startswith("00_"):
            continue
        files.append(("Zhuang Zi(庄子)", p))
    # Lie Zi
    for p in sorted((ROOT / "chapters" / "liezi").glob("*.tagged.md")):
        files.append(("Lie Zi(列子)", p))
    # Wen Zi
    for p in sorted((ROOT / "chapters" / "wenzi").glob("*.tagged.md")):
        files.append(("Wen Zi(文子)", p))
    return files


def parse_tags(text: str) -> List[Tuple[str, str]]:
    return [(t.strip(), n.strip()) for t, n in TAG_RE.findall(text)]


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debiased",
        action="store_true",
        help="Exclude aggregated/commentary files (e.g., zhuangzi 00_*) for a debiased leaderboard.",
    )
    args = parser.parse_args()

    files = target_files(debiased=args.debiased)
    if not files:
        raise RuntimeError("No philosophy tagged files found.")

    node_counts: Counter = Counter()
    node_counts_by_work: Dict[str, Counter] = defaultdict(Counter)
    edge_counts: Counter = Counter()

    for work, path in files:
        text = path.read_text(encoding="utf-8")
        tags = parse_tags(text)
        unique_nodes = set()

        for t, name in tags:
            key = (t, name)
            node_counts[key] += 1
            node_counts_by_work[work][key] += 1
            unique_nodes.add(key)

        # file-level co-occurrence
        for a, b in combinations(sorted(unique_nodes), 2):
            edge_counts[(a, b)] += 1

    nodes = []
    for (t, name), count in node_counts.items():
        node_id = f"{t}:{name}"
        nodes.append(
            {
                "id": node_id,
                "type": t,
                "name": name,
                "weight": count,
                "by_work": {w: c[(t, name)] for w, c in node_counts_by_work.items() if c[(t, name)] > 0},
            }
        )

    links = []
    for (a, b), c in edge_counts.items():
        if c < 2:
            continue
        links.append(
            {
                "source": f"{a[0]}:{a[1]}",
                "target": f"{b[0]}:{b[1]}",
                "weight": c,
            }
        )

    kg = {
        "metadata": {
            "scope": "Four philosophy classics",
            "works": ["Dao De Jing(道德经)", "Zhuang Zi(庄子)", "Lie Zi(列子)", "Wen Zi(文子)"],
            "source_files": [str(p.relative_to(ROOT)) for _, p in files],
            "cooccurrence_level": "file",
        },
        "nodes": nodes,
        "links": links,
    }
    out_kg = OUT_KG if not args.debiased else ROOT / "philosophy_kg_debiased.json"
    out_report = OUT_REPORT if not args.debiased else ROOT / "philosophy_kg_report_debiased.json"
    out_kg.write_text(json.dumps(kg, ensure_ascii=False, indent=2), encoding="utf-8")

    top_concepts = [
        {"name": n, "count": c}
        for (_, n), c in node_counts.most_common()
        if _ == "概念"
    ][:30]
    top_thoughts = [
        {"type": t, "name": n, "count": c}
        for (t, n), c in node_counts.most_common()
        if t in {"概念", "主体"}
    ][:30]

    report = {
        "total_files": len(files),
        "total_nodes": len(nodes),
        "total_links": len(links),
        "top_concepts": top_concepts[:15],
        "top_thoughts": top_thoughts[:15],
    }
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated: {out_kg}")
    print(f"Generated: {out_report}")
    print(f"Total nodes: {len(nodes)}, links: {len(links)}")
    print("Top concepts:")
    for i, item in enumerate(report["top_concepts"], start=1):
        print(f"{i:>2}. {item['name']} ({item['count']})")


if __name__ == "__main__":
    main()
