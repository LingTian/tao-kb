#!/usr/bin/env python3
"""
Crawl Taoist ritual/talisman texts from Wikisource into Ritual category.

Usage:
  python3 scripts/crawl_ritual_wikisource.py
  python3 scripts/crawl_ritual_wikisource.py --only 上清佩符文白券訣
"""

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from urllib.error import URLError


API_URL = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "tao-kb-bot/0.1 (https://github.com/LingTian/tao-kb)"
OUTPUT_ROOT = Path("texts") / "Ritual(科仪符箓)"


@dataclass
class RitualSource:
    titles: List[str]
    folder: str
    filename: str


SOURCES: List[RitualSource] = [
    RitualSource(["上清佩符文白券訣", "上清佩符文白券诀"], "Shang Qing Pei Fu(上清佩符文白券訣)", "shangqing_peifu_full.md"),
    RitualSource(["太極左仙公說神符經", "太极左仙公说神符经"], "Tai Ji Zuo Xian Gong Shen Fu Jing(太極左仙公說神符經)", "taiji_zuoxiangong_shenfu_full.md"),
    RitualSource(["太上三洞神呪", "太上三洞神咒"], "Tai Shang San Dong Shen Zhou(太上三洞神呪)", "taishang_sandong_shenzhou_full.md"),
    RitualSource(
        ["太上洞淵三昧神呪齋清旦行道儀", "太上洞渊三昧神咒斋清旦行道仪"],
        "Tai Shang Dong Yuan San Mei Shen Zhou Yi(太上洞淵三昧神呪齋清旦行道儀)",
        "taishang_dongyuan_sanmei_yi_full.md",
    ),
]


def sanitize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def strip_html(html: str) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>", "", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", "", html)
    html = re.sub(r"(?s)<[^>]+>", "", html)
    html = html.replace("&nbsp;", " ").replace("&amp;", "&")
    return sanitize_text(html)


def mediawiki_query(params: Dict[str, str]) -> Dict:
    query = urllib.parse.urlencode(params)
    url = f"{API_URL}?{query}"
    retries = 3
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(1.2 * attempt)
    raise RuntimeError(f"MediaWiki query failed after retries: {last_exc}")


def fetch_title_text(title: str) -> str:
    data = mediawiki_query(
        {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "explaintext": "1",
            "titles": title,
            "redirects": "1",
        }
    )
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return ""
    page = next(iter(pages.values()))
    text = sanitize_text(page.get("extract", ""))
    if text:
        return text

    parsed = mediawiki_query(
        {
            "action": "parse",
            "format": "json",
            "page": title,
            "prop": "text",
            "redirects": "1",
        }
    )
    html = parsed.get("parse", {}).get("text", {}).get("*", "")
    return strip_html(html)


def fetch_subpages(root_title: str) -> List[str]:
    subpages: List[str] = []
    cont = ""
    while True:
        params: Dict[str, str] = {
            "action": "query",
            "format": "json",
            "list": "allpages",
            "apprefix": f"{root_title}/",
            "apnamespace": "0",
            "aplimit": "500",
        }
        if cont:
            params["apcontinue"] = cont
        data = mediawiki_query(params)
        pages = data.get("query", {}).get("allpages", [])
        subpages.extend([p["title"] for p in pages if "title" in p])
        cont = data.get("continue", {}).get("apcontinue", "")
        if not cont:
            break
    return sorted(set(subpages))


def fetch_recursive_text(root_title: str, max_subpages: int = 200) -> str:
    sections: List[str] = []
    root_text = fetch_title_text(root_title)
    if root_text:
        sections.append(root_text)

    subpages = fetch_subpages(root_title)
    if max_subpages > 0:
        subpages = subpages[:max_subpages]

    for idx, sub in enumerate(subpages, start=1):
        try:
            sub_text = fetch_title_text(sub)
        except Exception:
            continue
        if not sub_text:
            continue
        sections.append(f"## {sub}\n\n{sub_text}")
        if idx % 20 == 0:
            print(f"  - fetched {idx}/{len(subpages)} subpages for {root_title}")
        time.sleep(0.12)

    return sanitize_text("\n\n".join(sections))


def save_markdown(path: Path, source_title: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {source_title}\n\n")
        f.write("> Source: https://zh.wikisource.org/wiki/")
        f.write(urllib.parse.quote(source_title))
        f.write("\n\n")
        f.write(content)
        f.write("\n")


def run(selected_titles: List[str], max_subpages: int) -> None:
    selected = set(selected_titles)
    targets = [s for s in SOURCES if not selected or any(t in selected for t in s.titles)]
    if not targets:
        print("No matched ritual titles.")
        return

    print(f"Start crawling {len(targets)} ritual/talisman texts...")
    success = 0
    failed = []

    for source in targets:
        try:
            used_title = ""
            text = ""
            for title in source.titles:
                text = fetch_recursive_text(title, max_subpages=max_subpages)
                if text:
                    used_title = title
                    break
            if not text:
                failed.append((source.titles[0], "empty extract or page not found"))
                print(f"[FAIL] {source.titles[0]}: empty extract.")
                continue

            output_path = OUTPUT_ROOT / source.folder / source.filename
            save_markdown(output_path, used_title, text)
            success += 1
            print(f"[OK] {used_title} -> {output_path}")
        except Exception as exc:
            failed.append((source.titles[0], str(exc)))
            print(f"[FAIL] {source.titles[0]}: {exc}")

    print("\nDone.")
    print(f"Success: {success}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failed details:")
        for title, reason in failed:
            print(f"- {title}: {reason}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl Taoist ritual texts from Wikisource")
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Only crawl specified titles.",
    )
    parser.add_argument(
        "--max-subpages",
        type=int,
        default=200,
        help="Max subpages per title (default: 200).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.only, args.max_subpages)
