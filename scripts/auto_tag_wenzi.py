#!/usr/bin/env python3
"""
Auto-tag Wenzi using existing tao-kb tagged lexicon.

Input:
  texts/Philosophy(哲学)/Wen Zi(文子)/wenzi_full.md

Output:
  chapters/wenzi/00_Wen_Zi.tagged.md
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "texts" / "Philosophy(哲学)" / "Wen Zi(文子)" / "wenzi_full.md"
OUT = ROOT / "chapters" / "wenzi" / "00_Wen_Zi.tagged.md"

TAG_RE = re.compile(r"〖@([^:]+):([^〗]+)〗")


def extract_lexicon() -> Dict[str, List[str]]:
    by_type_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for path in (ROOT / "chapters").rglob("*.tagged.md"):
        rel = path.relative_to(ROOT).as_posix()
        if "legacy" in rel or rel.startswith("chapters/wenzi/"):
            continue
        text = path.read_text(encoding="utf-8")
        for tag_type, name in TAG_RE.findall(text):
            name = name.strip()
            if len(name) < 2 or "|" in name:
                continue
            by_type_counts[tag_type][name] += 1

    by_type_terms: Dict[str, List[str]] = {}
    for tag_type, counts in by_type_counts.items():
        terms = [t for t, c in counts.items() if c >= 2]
        terms.sort(key=len, reverse=True)
        by_type_terms[tag_type] = terms
    return by_type_terms


def apply_tagging(raw_text: str, lexicon: Dict[str, List[str]]) -> Tuple[str, int]:
    total_replacements = 0
    lines = raw_text.splitlines()
    out_lines: List[str] = []

    for line in lines:
        if line.startswith("# "):
            out_lines.append("# 文子 (Wen Zi) - 自动标注试跑版")
            continue
        if line.startswith("> Source:"):
            out_lines.append(line)
            continue
        if not line.strip():
            out_lines.append(line)
            continue
        if line.startswith("卷") and " " in line:
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
    lines = tagged_text.splitlines()
    cleaned: List[str] = []

    for line in lines:
        if line.startswith("## "):
            content = line[3:]
            content = re.sub(r"〖@[^:]+:([^〗]+)〗", r"\1", content)
            cleaned.append("## " + content)
            continue
        if line.startswith("卷") and " " in line:
            cleaned.append(re.sub(r"〖@[^:]+:([^〗]+)〗", r"\1", line))
            continue
        cleaned.append(line)

    text = "\n".join(cleaned) + "\n"
    return text


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source not found: {SOURCE}")

    raw_text = SOURCE.read_text(encoding="utf-8")
    lexicon = extract_lexicon()
    tagged_text, replaced = apply_tagging(raw_text, lexicon)
    cleaned_text = cleanup_tagged_text(tagged_text)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(cleaned_text, encoding="utf-8")
    print(f"Generated: {OUT}")
    print(f"Replacements: {replaced}")
    print(f"Tag types used: {', '.join(sorted(k for k,v in lexicon.items() if v))}")


if __name__ == "__main__":
    main()
