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
RITUAL_DIR = ROOT / "texts" / "Ritual(科仪符箓)"
OUT_HTML = ROOT / "docs" / "index.html"
TAXONOMY_FILE = ROOT / "tag_taxonomy.json"

TAG_PATTERN = re.compile(r"〖@([^:]+):([^〗]+)〗")


def iter_tagged_files() -> List[Path]:
    files = []
    for path in CHAPTERS_DIR.rglob("*.tagged.md"):
        if "legacy" in path.parts:
            continue
        files.append(path)
    return sorted(files, key=lambda p: str(p).lower())


def iter_ritual_files() -> List[Path]:
    if not RITUAL_DIR.exists():
        return []
    files = [p for p in RITUAL_DIR.rglob("*.md") if p.is_file()]
    return sorted(files, key=lambda p: str(p).lower())


def classify_text_category_and_work(rel_path: str) -> Tuple[str, str]:
    if rel_path.startswith("chapters/zhuangzi/"):
        return "Philosophy(哲学)", "Zhuang Zi(庄子)"
    if rel_path.startswith("chapters/daodejing_"):
        return "Philosophy(哲学)", "Dao De Jing(道德经)"
    if rel_path.startswith("texts/Ritual(科仪符箓)/"):
        parts = rel_path.split("/")
        if len(parts) >= 4:
            return "Ritual(科仪符箓)", parts[2]
        return "Ritual(科仪符箓)", "Unknown"
    return "Other(其他)", "Unknown"


def sanitize_class_name(tag_type: str) -> str:
    safe = re.sub(r"\s+", "-", tag_type.strip())
    safe = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]", "-", safe)
    return safe or "unknown"


def load_taxonomy() -> Dict[str, str]:
    if not TAXONOMY_FILE.exists():
        return {}
    try:
        data = json.loads(TAXONOMY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


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

    idx = 1
    for path in iter_tagged_files():
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
                "textCategory": classify_text_category_and_work(rel)[0],
                "work": classify_text_category_and_work(rel)[1],
                "title": path.stem.replace(".tagged", ""),
                "tagCounts": local_stats,
                "html": "\n".join(html_lines),
            }
        )
        idx += 1

    # Include ritual corpus pages (plain markdown, no inline tags yet).
    for path in iter_ritual_files():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        local_stats: Dict[str, int] = {}
        html_lines = [render_line(line, local_stats) for line in text.splitlines()]
        chapters.append(
            {
                "id": idx,
                "path": rel,
                "textCategory": classify_text_category_and_work(rel)[0],
                "work": classify_text_category_and_work(rel)[1],
                "title": path.stem,
                "tagCounts": local_stats,
                "html": "\n".join(html_lines),
            }
        )
        idx += 1
    return chapters, total_stats


def render_html(chapters: List[Dict], total_stats: Dict[str, int], taxonomy: Dict[str, str]) -> str:
    category_to_types: Dict[str, List[str]] = {}
    for t in sorted(total_stats.keys()):
        c = taxonomy.get(t, "未分类")
        category_to_types.setdefault(c, []).append(t)

    payload_json = json.dumps(
        {
            "chapters": chapters,
            "tagTypes": sorted(total_stats.keys()),
            "tagStats": total_stats,
            "taxonomy": taxonomy,
            "categoryToTypes": category_to_types,
        },
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
    .tags {{ display: grid; gap: 10px; margin-top: 8px; }}
    .tag-group {{ border: 1px solid var(--border); border-radius: 10px; padding: 8px; background: #11141b; }}
    .tag-group-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    .tag-group-title {{ font-size: 13px; color: var(--accent); font-weight: 600; }}
    .tag-group-actions {{ display: flex; gap: 6px; }}
    .chip-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
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
      <select id="categoryFilter" class="select">
        <option value="all">全部分类</option>
        <option value="Philosophy(哲学)">Philosophy(哲学)</option>
        <option value="Ritual(科仪符箓)">Ritual(科仪符箓)</option>
      </select>
      <select id="workFilter" class="select">
        <option value="all">全部典籍</option>
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
      textCategory: "all",
      work: "all"
    }};

    const chapterListEl = document.getElementById("chapterList");
    const readerEl = document.getElementById("reader");
    const chipsEl = document.getElementById("tagChips");
    const chapterMetaEl = document.getElementById("chapterMeta");
    const searchInput = document.getElementById("searchInput");
    const categoryFilter = document.getElementById("categoryFilter");
    const workFilter = document.getElementById("workFilter");
    const highlightSwitch = document.getElementById("highlightSwitch");

    function listWorksByCategory() {{
      const works = new Set();
      DATA.chapters.forEach(c => {{
        if (state.textCategory === "all" || c.textCategory === state.textCategory) {{
          works.add(c.work);
        }}
      }});
      return Array.from(works).sort();
    }}

    function renderWorkOptions() {{
      const works = listWorksByCategory();
      workFilter.innerHTML = [
        '<option value="all">全部典籍</option>',
        ...works.map(w => `<option value="${{w}}">${{w}}</option>`)
      ].join("");
      if (!works.includes(state.work)) {{
        state.work = "all";
      }}
      workFilter.value = state.work;
    }}

    function getFilteredChapters() {{
      return DATA.chapters.filter(c => {{
        const byCategory = state.textCategory === "all" || c.textCategory === state.textCategory;
        if (!byCategory) return false;
        const byWork = state.work === "all" || c.work === state.work;
        if (!byWork) return false;
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
          <div class="book">${{c.textCategory}} / ${{c.work}}</div>
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
      const categories = Object.keys(DATA.categoryToTypes).sort();
      chipsEl.innerHTML = categories.map(cat => {{
        const types = DATA.categoryToTypes[cat] || [];
        const allOn = types.every(t => state.enabledTypes.has(t));
        const chips = types.map(t => {{
          const off = state.enabledTypes.has(t) ? "" : "off";
          const n = DATA.tagStats[t] || 0;
          return `<button class="chip ${{off}}" data-type="${{t}}">${{t}} (${{n}})</button>`;
        }}).join("");
        return `
          <section class="tag-group" data-category="${{cat}}">
            <div class="tag-group-head">
              <span class="tag-group-title">${{cat}}</span>
              <div class="tag-group-actions">
                <button class="chip category-toggle" data-category="${{cat}}" data-mode="${{allOn ? "off" : "on"}}">
                  ${{allOn ? "全关" : "全开"}}
                </button>
              </div>
            </div>
            <div class="chip-row">${{chips}}</div>
          </section>
        `;
      }}).join("");

      for (const el of chipsEl.querySelectorAll(".chip[data-type]")) {{
        el.addEventListener("click", () => {{
          const t = el.dataset.type;
          if (state.enabledTypes.has(t)) state.enabledTypes.delete(t);
          else state.enabledTypes.add(t);
          renderReader();
          renderTagChips();
        }});
      }}

      for (const el of chipsEl.querySelectorAll(".category-toggle")) {{
        el.addEventListener("click", () => {{
          const cat = el.dataset.category;
          const mode = el.dataset.mode;
          const types = DATA.categoryToTypes[cat] || [];
          if (mode === "on") {{
            types.forEach(t => state.enabledTypes.add(t));
          }} else {{
            types.forEach(t => state.enabledTypes.delete(t));
          }}
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
      chapterMetaEl.textContent = `${{chapter.textCategory}} / ${{chapter.work}} · ${{chapter.path}}`;

      const tags = readerEl.querySelectorAll(".tag");
      tags.forEach(el => {{
        const t = el.dataset.tagType;
        const typeEnabled = state.enabledTypes.has(t);
        const show = state.highlight && typeEnabled;
        el.classList.toggle("hidden-tag", !show);
      }});
    }}

    function renderAll() {{
      renderWorkOptions();
      renderChapterList();
      renderTagChips();
      renderReader();
    }}

    searchInput.addEventListener("input", e => {{
      state.keyword = e.target.value.trim();
      renderAll();
    }});
    categoryFilter.addEventListener("change", e => {{
      state.textCategory = e.target.value;
      state.work = "all";
      renderAll();
    }});
    workFilter.addEventListener("change", e => {{
      state.work = e.target.value;
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
    taxonomy = load_taxonomy()
    chapters, total_stats = build_payload()
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(chapters, total_stats, taxonomy), encoding="utf-8")
    print(f"Rendered {len(chapters)} chapters -> {OUT_HTML}")
    print(f"Tag types: {', '.join(sorted(total_stats.keys()))}")


if __name__ == "__main__":
    main()
