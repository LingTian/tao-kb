#!/usr/bin/env python3
"""
Batch auto-tag multiple Taoist classics using existing tao-kb tagged lexicon.

Usage:
  python3 scripts/auto_tag_batch.py
  python3 scripts/auto_tag_batch.py --only 淮南子 抱朴子
  python3 scripts/auto_tag_batch.py --dry-run

Source texts should be under texts/Philosophy(哲学)/ or texts/Alchemy(丹道体系)/.
Output goes to chapters/<canonical_name>/.
"""

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"〖@([^:]+):([^〗]+)〗")


@dataclass
class ClassicSource:
    name: str
    folder: str
    filename: str
    category: str  # "Philosophy(哲学)" or "Alchemy(丹道体系)"
    chapters: List[Tuple[str, str]]  # (number_prefix, title_pattern)


CLASSICS: List[ClassicSource] = [
    ClassicSource(
        name="淮南子",
        folder="Huai Nan Zi(淮南子)",
        filename="huainanzi_full.md",
        category="Alchemy(丹道体系)/Reference Classics(相关典籍)",
        chapters=[],  # will be split by script
    ),
    ClassicSource(
        name="抱朴子",
        folder="Bao Pu Zi(抱朴子)",
        filename="baopuzi_full.md",
        category="Alchemy(丹道体系)/Reference Classics(相关典籍)",
        chapters=[],
    ),
    ClassicSource(
        name="周易参同契",
        folder="Zhou Yi Can Tong Qi(周易参同契)",
        filename="cantongqi_full.md",
        category="Alchemy(丹道体系)/Reference Classics(相关典籍)",
        chapters=[],
    ),
    ClassicSource(
        name="黄帝阴符经",
        folder="Huang Di Yin Fu Jing(黄帝阴符经)",
        filename="yinfujing_full.md",
        category="Alchemy(丹道体系)/Reference Classics(相关典籍)",
        chapters=[],
    ),
    ClassicSource(
        name="清静经",
        folder="Qing Jing Jing(清静经)",
        filename="qingjingjing_full.md",
        category="Alchemy(丹道体系)/Reference Classics(相关典籍)",
        chapters=[],
    ),
    # New additions
    ClassicSource(
        name="关尹子",
        folder="Guan Yin Zi(关尹子)",
        filename="guanyinzi_full.md",
        category="Alchemy(丹道体系)/Reference Classics(相关典籍)",
        chapters=[],
    ),
    ClassicSource(
        name="鹖冠子",
        folder="He Guan Zi(鹖冠子)",
        filename="heguanzi_full.md",
        category="Alchemy(丹道体系)/Reference Classics(相关典籍)",
        chapters=[],
    ),
    ClassicSource(
        name="老子想尔注",
        folder="Lao Xiang Er(老子想尔注)",
        filename="laoxianger_full.md",
        category="Alchemy(丹道体系)/Reference Classics(相关典籍)",
        chapters=[],
    ),
    ClassicSource(
        name="管子",
        folder="Guan Zi(管子)",
        filename="guanzi_full.md",
        category="Alchemy(丹道体系)/Reference Classics(相关典籍)",
        chapters=[],
    ),
]


def extract_lexicon(exclude_patterns: List[str]) -> Dict[str, List[str]]:
    """
    Build lexicon from existing tagged chapters.
    Exclude patterns to avoid including output we're about to generate.
    """
    by_type_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for path in (ROOT / "chapters").rglob("*.tagged.md"):
        rel = path.relative_to(ROOT).as_posix()
        if "legacy" in rel:
            continue
        if any(pat in rel for pat in exclude_patterns):
            continue
        text = path.read_text(encoding="utf-8")
        for tag_type, name in TAG_RE.findall(text):
            name = name.strip()
            if len(name) < 2:
                continue
            if "|" in name:
                continue
            by_type_counts[tag_type][name] += 1

    by_type_terms: Dict[str, List[str]] = {}
    for tag_type, counts in by_type_counts.items():
        terms = [t for t, c in counts.items() if c >= 2]
        terms.sort(key=len, reverse=True)
        by_type_terms[tag_type] = terms
    return by_type_terms


def apply_tagging(raw_text: str, lexicon: Dict[str, List[str]], classic_name: str) -> Tuple[str, int]:
    """
    Apply longest-match replacement by type.
    """
    total_replacements = 0
    lines = raw_text.splitlines()
    out_lines: List[str] = []

    for line in lines:
        if line.startswith("# "):
            out_lines.append(f"# {classic_name} - 自动标注版")
            continue
        if line.startswith("> Source:"):
            out_lines.append(line)
            continue
        if not line.strip():
            out_lines.append(line)
            continue

        segments = re.split(r"(〖@[^〗]+〗)", line)
        for i, seg in enumerate(segments):
            if not seg or seg.startswith("〖@"):
                continue
            for tag_type, terms in lexicon.items():
                if line.startswith("## ") and tag_type in {"人物", "地名", "生物", "主体"}:
                    continue
                for term in terms:
                    new_seg, n = re.subn(re.escape(term), f"〖@{tag_type}:{term}〗", seg)
                    if n:
                        seg = new_seg
                        total_replacements += n
            segments[i] = seg
        out_lines.append("".join(segments))

    return "\n".join(out_lines) + "\n", total_replacements


def cleanup_tagged_text(tagged_text: str) -> str:
    """
    Second-pass cleanup for obvious over-tagging.
    """
    lines = tagged_text.splitlines()
    cleaned: List[str] = []

    for line in lines:
        if line.startswith("## "):
            content = line[3:]
            content = re.sub(r"〖@[^:]+:([^〗]+)〗", r"\1", content)
            cleaned.append("## " + content)
            continue
        cleaned.append(line)

    text = "\n".join(cleaned) + "\n"
    return text


def process_classic(classic: ClassicSource, lexicon: Dict[str, List[str]], dry_run: bool) -> Dict:
    """
    Process a single classic: tag, clean, and save.
    """
    source_path = ROOT / "texts" / classic.category / classic.folder / classic.filename
    if not source_path.exists():
        return {"name": classic.name, "status": "skip", "reason": "source file not found"}

    raw_text = source_path.read_text(encoding="utf-8")
    tagged_text, replaced = apply_tagging(raw_text, lexicon, classic.name)
    cleaned_text = cleanup_tagged_text(tagged_text)

    # Simplify directory name
    canonical_dir = classic.name.replace(" ", "_")
    out_dir = ROOT / "chapters" / canonical_dir
    out_file = out_dir / f"00_{canonical_dir}.tagged.md"

    if dry_run:
        return {
            "name": classic.name,
            "status": "dry-run",
            "source": str(source_path.relative_to(ROOT)),
            "output": str(out_file.relative_to(ROOT)),
            "replacements": replaced,
            "tag_types": ", ".join(sorted(k for k, v in lexicon.items() if v)),
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(cleaned_text, encoding="utf-8")

    return {
        "name": classic.name,
        "status": "done",
        "output": str(out_file.relative_to(ROOT)),
        "replacements": replaced,
        "tag_types": ", ".join(sorted(k for k, v in lexicon.items() if v)),
    }


def run(selected: List[str], dry_run: bool) -> None:
    selected_set = set(selected)
    targets = [c for c in CLASSICS if not selected_set or c.name in selected_set]

    if not targets:
        print("No matched classics. Use --only with exact Chinese title.")
        return

    # Build lexicon excluding targets we're about to process
    exclude_patterns = [c.folder for c in targets]
    lexicon = extract_lexicon(exclude_patterns)

    print(f"Lexicon built from existing tagged files:")
    for tag_type, terms in sorted(lexicon.items()):
        print(f"  {tag_type}: {len(terms)} terms")
    print()

    print(f"Processing {len(targets)} classic(s)...\n")
    results = []
    for classic in targets:
        result = process_classic(classic, lexicon, dry_run)
        results.append(result)
        if dry_run:
            print(f"[DRY-RUN] {result['name']}")
            print(f"  Source: {result['source']}")
            print(f"  Output: {result['output']}")
            print(f"  Replacements: {result['replacements']}")
            print(f"  Tag types: {result['tag_types']}")
        elif result["status"] == "skip":
            print(f"[SKIP] {result['name']}: {result['reason']}")
        else:
            print(f"[OK] {result['name']} -> {result['output']}")
            print(f"  Replacements: {result['replacements']}")
        print()

    print("Done.")
    print(f"Processed: {sum(1 for r in results if r['status'] == 'done')}")
    print(f"Skipped: {sum(1 for r in results if r['status'] == 'skip')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch auto-tag Taoist classics")
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Only tag specified classics, e.g. --only 淮南子 抱朴子",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.only, args.dry_run)
