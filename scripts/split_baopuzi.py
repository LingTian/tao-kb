#!/usr/bin/env python3
"""
Split Bao Pu Zi from single merged file into chapter-based files.
Following the same pattern as Zhuangzi/Liezi/Wenzi.

Input:
  chapters/抱朴子/00_抱朴子.tagged.md

Output:
  chapters/抱朴子/01_暢玄.tagged.md
  chapters/抱朴子/02_論仙.tagged.md
  ...
"""

import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "chapters", "抱朴子", "00_抱朴子.tagged.md")
OUTPUT_DIR = os.path.join(ROOT, "chapters", "抱朴子")

# Chapter name mapping for 內篇 (20 chapters) + 外篇 (52 chapters)
INNER_CHAPTERS = [
    "暢玄", "論仙", "對俗", "金丹", "至理",
    "微旨", "塞難", "釋滯", "道意", "明本",
    "仙藥", "辨問", "極言", "勤求", "雜應",
    "黃白", "登涉", "地真", "遐覽", "袪惑",
]

OUTER_CHAPTERS = [
    "嘉遁", "逸民", "勖學", "崇教", "君道",
    "臣節", "良規", "時難", "官理", "務正",
    "貴賢", "任能", "欽士", "用刑", "審舉",
    "交際", "備闕", "擢才", "任命", "名實",
    "清鑒", "行品", "弭訟", "酒誡", "疾謬",
    "譏惑", "刺驕", "百里", "接疏", "鈞世",
    "省煩", "尚博", "漢過", "吳失", "守塉",
    "安貧", "仁明", "博喻", "廣譬", "辭義",
    "循本", "應嘲", "喻蔽", "百家", "文行",
    "正郭", "彈禰", "詰鮑", "知止", "窮達",
    "重言", "自敘",
]


def split_baopuzi():
    if not os.path.exists(SOURCE):
        print(f"Source not found: {SOURCE}")
        return

    with open(SOURCE, "r", encoding="utf-8") as f:
        content = f.read()

    # Match ## 抱朴子/卷XX sections
    section_pattern = re.compile(r'\n## 抱朴子/卷(\d+)')
    matches = list(section_pattern.finditer(content))

    if not matches:
        print("No sections found. File may need to be re-fetched from Wikisource.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Build chapter name lookup
    all_chapters = INNER_CHAPTERS + OUTER_CHAPTERS

    created = 0
    for i, match in enumerate(matches):
        vol_num = int(match.group(1))
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

        section_content = content[start:end].strip()

        # Get chapter name
        if vol_num <= len(all_chapters):
            chapter_name = all_chapters[vol_num - 1]
            filename = f"{vol_num:02d}_{chapter_name}.tagged.md"
        else:
            filename = f"{vol_num:02d}.tagged.md"

        output_path = os.path.join(OUTPUT_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(section_content)

        print(f"  Created: {filename}")
        created += 1

    print(f"\nSplit into {created} chapters.")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    split_baopuzi()
