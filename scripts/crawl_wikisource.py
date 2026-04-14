#!/usr/bin/env python3
"""
Fetch Taoist classics from Wikisource (MediaWiki API).

Usage:
  python3 scripts/crawl_wikisource.py
  python3 scripts/crawl_wikisource.py --only 列子 抱朴子
"""

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List
from urllib.error import URLError


API_URL = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "tao-kb-bot/0.1 (https://github.com/LingTian/tao-kb)"
OUTPUT_ROOT = os.path.join("texts", "Philosophy(哲学)")


@dataclass
class Source:
    titles: List[str]
    folder: str
    filename: str


SOURCES: List[Source] = [
    Source(["列子"], "Lie Zi(列子)", "liezi_full.md"),
    Source(["文子"], "Wen Zi(文子)", "wenzi_full.md"),
    Source(["淮南子"], "Huai Nan Zi(淮南子)", "huainanzi_full.md"),
    Source(["抱朴子"], "Bao Pu Zi(抱朴子)", "baopuzi_full.md"),
    Source(["周易參同契", "周易参同契"], "Zhou Yi Can Tong Qi(周易参同契)", "cantongqi_full.md"),
    Source(["黃帝陰符經", "黄帝阴符经"], "Huang Di Yin Fu Jing(黄帝阴符经)", "yinfujing_full.md"),
    Source(
        ["太上老君說常清靜經", "太上老君说常清静经", "清靜經", "清静经"],
        "Qing Jing Jing(清静经)",
        "qingjingjing_full.md",
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

    # Fallback: some pages are template-heavy and return empty extracts.
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
    """
    List subpages for a title, e.g. 抱朴子/卷01.
    """
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


def fetch_recursive_text(root_title: str, max_subpages: int = 0) -> str:
    """
    Fetch root page and all child pages, then combine as one markdown text.
    """
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
        time.sleep(0.15)

    return sanitize_text("\n\n".join(sections))


def ensure_folder(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_markdown(path: str, title: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write("> Source: https://zh.wikisource.org/wiki/")
        f.write(urllib.parse.quote(title))
        f.write("\n\n")
        f.write(content)
        f.write("\n")


def run(selected_titles: List[str], max_subpages: int) -> None:
    selected = set(selected_titles)
    targets = [s for s in SOURCES if not selected or any(t in selected for t in s.titles)]

    if not targets:
        print("No matched titles. Use --only with exact Chinese title.")
        return

    print(f"Start crawling {len(targets)} classics from Wikisource...")
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

            folder = os.path.join(OUTPUT_ROOT, source.folder)
            ensure_folder(folder)
            output_path = os.path.join(folder, source.filename)
            save_markdown(output_path, used_title, text)
            success += 1
            print(f"[OK] {used_title} -> {output_path}")
            time.sleep(0.8)
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
    parser = argparse.ArgumentParser(description="Crawl Taoist classics from Wikisource")
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Only crawl specified titles, e.g. --only 列子 抱朴子",
    )
    parser.add_argument(
        "--max-subpages",
        type=int,
        default=0,
        help="Limit fetched subpages per title (0 means no limit).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.only, args.max_subpages)
