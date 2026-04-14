#!/usr/bin/env python3
"""
Crawl core Daoist canon texts for Alchemy systems.
"""

import argparse
import json
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
OUTPUT_ROOT = Path("texts") / "Alchemy(丹道体系)"


@dataclass
class CanonSource:
    system: str
    titles: List[str]
    filename: str
    label: str


SOURCES: List[CanonSource] = [
    CanonSource("Shangqing(上清经系)", ["上清大洞真經", "上清大洞真经"], "shangqing_dadong_zhenjing.md", "上清大洞真经"),
    CanonSource(
        "Shangqing(上清经系)",
        ["黃庭內景經", "黄庭内景经", "黃庭外景經", "黄庭外景经", "黃庭經", "黄庭经"],
        "huangtingjing.md",
        "黄庭经",
    ),
    CanonSource(
        "Lingbao(灵宝经系)",
        [
            "靈寶度人經",
            "灵宝度人经",
            "靈寶無量度人上品妙經",
            "灵宝无量度人上品妙经",
            "元始無量度人上品妙經",
            "元始无量度人上品妙经",
        ],
        "lingbao_durenjing.md",
        "灵宝度人经",
    ),
    CanonSource(
        "Lingbao(灵宝经系)",
        ["太上洞玄靈寶五符序", "太上洞玄灵宝五符序", "太上靈寶五符序", "太上灵宝五符序"],
        "taishang_lingbao_wufuxu.md",
        "太上灵宝五符序",
    ),
    CanonSource("Zhengyi(正一经系)", ["正一法文", "正一法文天師教戒科經", "正一法文天师教戒科经"], "zhengyi_fawen.md", "正一法文"),
    CanonSource(
        "Zhengyi(正一经系)",
        ["三五都功經籙", "三五都功经箓", "正一修真略儀", "正一修真略仪"],
        "sanwu_dugong_jinglu.md",
        "三五都功经箓",
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
    last_exc = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(1.2 * attempt)
    raise RuntimeError(f"MediaWiki query failed: {last_exc}")


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
        {"action": "parse", "format": "json", "page": title, "prop": "text", "redirects": "1"}
    )
    html = parsed.get("parse", {}).get("text", {}).get("*", "")
    return strip_html(html)


def fetch_subpages(root_title: str) -> List[str]:
    subpages: List[str] = []
    cont = ""
    while True:
        params = {
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
        subpages.extend([p["title"] for p in data.get("query", {}).get("allpages", []) if "title" in p])
        cont = data.get("continue", {}).get("apcontinue", "")
        if not cont:
            break
    return sorted(set(subpages))


def fetch_recursive_text(root_title: str) -> str:
    sections: List[str] = []
    root = fetch_title_text(root_title)
    if root:
        sections.append(root)
    for sub in fetch_subpages(root_title):
        sub_text = fetch_title_text(sub)
        if sub_text:
            sections.append(f"## {sub}\n\n{sub_text}")
            time.sleep(0.1)
    return sanitize_text("\n\n".join(sections))


def fetch_linked_chapters(title: str) -> str:
    """Follow chapter links from catalog-style root pages."""
    data = mediawiki_query({"action": "parse", "format": "json", "page": title, "prop": "links", "redirects": "1"})
    links = data.get("parse", {}).get("links", [])
    chapter_titles: List[str] = []
    for item in links:
        if item.get("ns") != 0:
            continue
        link_title = item.get("*", "").strip()
        if "/" not in link_title:
            continue
        if link_title.endswith("/全覽") or link_title.endswith("/序"):
            continue
        chapter_titles.append(link_title)

    blocks: List[str] = []
    seen = set()
    for chapter in chapter_titles:
        if chapter in seen:
            continue
        seen.add(chapter)
        text = fetch_title_text(chapter)
        if text:
            blocks.append(f"## {chapter}\n\n{text}")
            time.sleep(0.1)
    return sanitize_text("\n\n".join(blocks))


def save(path: Path, source_title: str, display_label: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# {display_label}\n\n> Source: https://zh.wikisource.org/wiki/{urllib.parse.quote(source_title)}\n\n{content}\n",
        encoding="utf-8",
    )


def run(only: List[str]) -> None:
    selected = set(only)
    targets = [s for s in SOURCES if not selected or s.label in selected or any(t in selected for t in s.titles)]
    print(f"Start crawling {len(targets)} alchemy canon texts...")
    ok = 0
    fail = []
    for s in targets:
        used = ""
        text = ""
        try:
            # Special merge strategy for Huangtingjing family pages.
            if s.label == "黄庭经":
                parts = []
                used_titles = []
                for t in s.titles:
                    t_text = fetch_recursive_text(t)
                    if t in {"黃庭內景經", "黄庭内景经"} and len(t_text) < 200:
                        t_text = fetch_linked_chapters(t)
                    # skip disambiguation-like short pages
                    if not t_text or len(t_text) < 200:
                        continue
                    if t in {"黃庭內景經", "黄庭内景经", "黃庭外景經", "黄庭外景经"}:
                        parts.append(f"## {t}\n\n{t_text}")
                    else:
                        parts.append(t_text)
                    used_titles.append(t)
                text = sanitize_text("\n\n".join(parts))
                if used_titles:
                    used = " / ".join(used_titles)
            else:
                for t in s.titles:
                    text = fetch_recursive_text(t)
                    if text:
                        used = t
                        break
            if not text:
                fail.append((s.label, "not found/empty"))
                print(f"[FAIL] {s.label}: not found/empty")
                continue
            out = OUTPUT_ROOT / s.system / f"{s.label}({s.label})" / s.filename
            save(out, used, s.label, text)
            print(f"[OK] {s.label} -> {out}")
            ok += 1
        except Exception as exc:
            fail.append((s.label, str(exc)))
            print(f"[FAIL] {s.label}: {exc}")

    print("\nDone.")
    print(f"Success: {ok}")
    print(f"Failed: {len(fail)}")
    if fail:
        for k, v in fail:
            print(f"- {k}: {v}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--only", nargs="*", default=[], help="Only crawl given labels/titles")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.only)
