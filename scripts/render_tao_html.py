#!/usr/bin/env python3
"""
Render a static online reader for tao-kb tagged chapters.

Output:
  - docs/index.html
"""

import json
import os
import re
from html import escape
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS_DIR = ROOT / "chapters"
OUT_HTML = ROOT / "docs" / "index.html"

TAG_PATTERN = re.compile(r"〖@([^:]+):([^〗]+)〗")


def iter_tagged_files() -> List[Path]:
    files = []
    for path in CHAPTERS_DIR.rglob("*.tagged.md"):
        if "legacy" in path.parts:
            continue
        files.append(path)
    return sorted(files, key=lambda p: str(p).lower())


def classify_book(rel_path: str) -> str:
    if rel_path.startswith("chapters/zhuangzi/"):
        return "庄子"
    if rel_path.startswith("chapters/daodejing_"):
        return "道德经"
    return "其他"


def sanitize_class_name(tag_type: str) -> str:
    safe = re.sub(r"\s+", "-", tag_type.strip())
    safe = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]", "-", safe)
    return safe or "unknown"


def render_line(line: str, stats: Dict[str, int]) -> str:
    line = line.rstrip("\n")

    # Headings
    if line.startswith("### "):
        return f"<h3>{escape(line[4:])}</h3>"
    if line.startswith("## "):
        return f"<h2>{escape(line[3:])}</h2>"
    if line.startswith("# "):
        return f"<h1>{escape(line[2:])}</h1>"
    if not line.strip():
        return "<p class='blank'></p>"

    pieces: List[str] = []
    last = 0
    for m in TAG_PATTERN.finditer(line):
        start, end = m.span()
        tag_type, tag_text = m.group(1).strip(), m.group(2).strip()
        tag_class = sanitize_class_name(tag_type)
        stats[tag_type] = stats.get(tag_type, 0) + 1

        pieces.append(escape(line[last:start]))
        pieces.append(
            f"<span class='tag tag-{tag_class}' data-tag-type='{escape(tag_type)}' "
            f"title='{escape(tag_type)}'>{escape(tag_text)}</span>"
        )
        last = end

    pieces.append(escape(line[last:]))
    return f"<p>{''.join(pieces)}</p>"


def build_payload() -> Tuple[List[Dict], Dict[str, int]]:
    chapters = []
    total_stats: Dict[str, int] = {}

    for idx, path in enumerate(iter_tagged_files(), start=1):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        local_stats: Dict[str, int] = {}
        html_lines = [render_line(line, local_stats) for line in text.splitlines()]

        for k, v in local_stats.items():
            total_stats[k] = total_stats.get(k, 0) + v

        chapters.append(
            {
                "id": idx,
                "path": rel,
                "book": classify_book(rel),
                "title": path.stem.replace(".tagged", ""),
                "tagCounts": local_stats,
                "html": "\n".join(html_lines),
            }
        )
    return chapters, total_stats


def render_html(chapters: List[Dict], total_stats: Dict[str, int]) -> str:
    payload_json = json.dumps(
        {"chapters": chapters, "tagTypes": sorted(total_stats.keys()), "tagStats": total_stats},
        ensure_ascii=False,
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>tao-kb 在线阅读器</title>
  <style>
    :root {{
      --bg: #0f1115;
      --panel: #171a21;
      --text: #e6e6e6;
      --muted: #9aa0aa;
      --accent: #7dd3fc;
      --border: #2a3040;
    }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; background: var(--bg); color: var(--text); }}
    .app {{ display: grid; grid-template-columns: 320px 1fr; min-height: 100vh; }}
    .sidebar {{ border-right: 1px solid var(--border); background: var(--panel); padding: 14px; overflow: auto; }}
    .main {{ padding: 20px 28px; overflow: auto; }}
    h1, h2, h3 {{ margin-top: 1.1em; margin-bottom: 0.5em; }}
    p {{ line-height: 1.85; margin: 0.2em 0; white-space: pre-wrap; }}
    .blank {{ height: 0.7em; }}
    .title {{ font-size: 20px; font-weight: 700; margin-bottom: 8px; }}
    .sub {{ color: var(--muted); font-size: 13px; margin-bottom: 12px; }}
    .search, .select {{ width: 100%; box-sizing: border-box; background: #11141b; color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; margin-bottom: 8px; }}
    .chapter-list {{ margin-top: 8px; }}
    .chapter-item {{ width: 100%; text-align: left; background: transparent; border: 1px solid transparent; color: var(--text); border-radius: 8px; padding: 8px; margin-bottom: 6px; cursor: pointer; }}
    .chapter-item:hover {{ border-color: var(--border); background: #11141b; }}
    .chapter-item.active {{ border-color: var(--accent); background: rgba(125, 211, 252, 0.08); }}
    .book {{ color: var(--accent); font-size: 12px; }}
    .path {{ color: var(--muted); font-size: 11px; margin-top: 2px; }}
    .toolbar {{ position: sticky; top: 0; background: var(--bg); padding-bottom: 10px; margin-bottom: 8px; border-bottom: 1px solid var(--border); }}
    .switch {{ display: inline-flex; align-items: center; gap: 6px; margin-right: 12px; color: var(--muted); font-size: 13px; }}
    .tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .chip {{ border: 1px solid var(--border); border-radius: 999px; padding: 4px 8px; font-size: 12px; cursor: pointer; color: var(--text); background: #11141b; }}
    .chip.off {{ opacity: 0.35; }}
    .tag {{ border-radius: 4px; padding: 0 2px; }}
    .tag-人物 {{ background: rgba(251, 146, 60, 0.25); }}
    .tag-地名 {{ background: rgba(56, 189, 248, 0.26); }}
    .tag-概念 {{ background: rgba(167, 139, 250, 0.26); }}
    .tag-境界 {{ background: rgba(52, 211, 153, 0.26); }}
    .tag-生物 {{ background: rgba(250, 204, 21, 0.24); }}
    .tag-隐喻 {{ background: rgba(244, 114, 182, 0.24); }}
    .tag-对立 {{ background: rgba(239, 68, 68, 0.28); }}
    .hidden-tag {{ background: transparent !important; color: inherit !important; }}
    @media (max-width: 900px) {{
      .app {{ grid-template-columns: 1fr; }}
      .sidebar {{ border-right: none; border-bottom: 1px solid var(--border); max-height: 38vh; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="title">tao-kb 阅读器</div>
      <div class="sub">按标注类型高亮阅读</div>
      <select id="bookFilter" class="select">
        <option value="all">全部文本</option>
        <option value="道德经">道德经</option>
        <option value="庄子">庄子</option>
      </select>
      <input id="searchInput" class="search" placeholder="搜索章节名或路径..." />
      <div id="chapterList" class="chapter-list"></div>
    </aside>
    <main class="main">
      <div class="toolbar">
        <label class="switch"><input id="highlightSwitch" type="checkbox" checked />显示高亮</label>
        <span id="chapterMeta" class="sub"></span>
        <div id="tagChips" class="tags"></div>
      </div>
      <article id="reader"></article>
    </main>
  </div>
  <script>
    const DATA = {payload_json};
    const state = {{
      currentId: DATA.chapters[0]?.id ?? null,
      enabledTypes: new Set(DATA.tagTypes),
      highlight: true,
      keyword: "",
      book: "all"
    }};

    const chapterListEl = document.getElementById("chapterList");
    const readerEl = document.getElementById("reader");
    const chipsEl = document.getElementById("tagChips");
    const chapterMetaEl = document.getElementById("chapterMeta");
    const searchInput = document.getElementById("searchInput");
    const bookFilter = document.getElementById("bookFilter");
    const highlightSwitch = document.getElementById("highlightSwitch");

    function getFilteredChapters() {{
      return DATA.chapters.filter(c => {{
        const byBook = state.book === "all" || c.book === state.book;
        if (!byBook) return false;
        if (!state.keyword) return true;
        const hay = (c.title + " " + c.path).toLowerCase();
        return hay.includes(state.keyword.toLowerCase());
      }});
    }}

    function renderChapterList() {{
      const chapters = getFilteredChapters();
      if (!chapters.find(c => c.id === state.currentId) && chapters[0]) {{
        state.currentId = chapters[0].id;
      }}
      chapterListEl.innerHTML = chapters.map(c => `
        <button class="chapter-item ${{c.id === state.currentId ? "active" : ""}}" data-id="${{c.id}}">
          <div>${{c.title}}</div>
          <div class="book">${{c.book}}</div>
          <div class="path">${{c.path}}</div>
        </button>
      `).join("");
      for (const el of chapterListEl.querySelectorAll(".chapter-item")) {{
        el.addEventListener("click", () => {{
          state.currentId = Number(el.dataset.id);
          renderAll();
        }});
      }}
    }}

    function renderTagChips() {{
      chipsEl.innerHTML = DATA.tagTypes.map(t => {{
        const off = state.enabledTypes.has(t) ? "" : "off";
        const n = DATA.tagStats[t] || 0;
        return `<button class="chip ${{off}}" data-type="${{t}}">${{t}} (${{n}})</button>`;
      }}).join("");
      for (const el of chipsEl.querySelectorAll(".chip")) {{
        el.addEventListener("click", () => {{
          const t = el.dataset.type;
          if (state.enabledTypes.has(t)) state.enabledTypes.delete(t);
          else state.enabledTypes.add(t);
          renderReader();
          renderTagChips();
        }});
      }}
    }}

    function renderReader() {{
      const chapter = DATA.chapters.find(c => c.id === state.currentId);
      if (!chapter) {{
        readerEl.innerHTML = "<p>没有匹配章节。</p>";
        chapterMetaEl.textContent = "";
        return;
      }}
      readerEl.innerHTML = chapter.html;
      chapterMetaEl.textContent = `${{chapter.book}} · ${{chapter.path}}`;

      const tags = readerEl.querySelectorAll(".tag");
      tags.forEach(el => {{
        const t = el.dataset.tagType;
        const typeEnabled = state.enabledTypes.has(t);
        const show = state.highlight && typeEnabled;
        el.classList.toggle("hidden-tag", !show);
      }});
    }}

    function renderAll() {{
      renderChapterList();
      renderTagChips();
      renderReader();
    }}

    searchInput.addEventListener("input", e => {{
      state.keyword = e.target.value.trim();
      renderAll();
    }});
    bookFilter.addEventListener("change", e => {{
      state.book = e.target.value;
      renderAll();
    }});
    highlightSwitch.addEventListener("change", e => {{
      state.highlight = e.target.checked;
      renderReader();
    }});

    renderAll();
  </script>
</body>
</html>
"""


def main() -> None:
    chapters, total_stats = build_payload()
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(chapters, total_stats), encoding="utf-8")
    print(f"Rendered {len(chapters)} chapters -> {OUT_HTML}")
    print(f"Tag types: {', '.join(sorted(total_stats.keys()))}")


if __name__ == "__main__":
    main()
