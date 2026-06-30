#!/usr/bin/env python3
"""Build a multi-language in-browser course reader.

For each language we split the course markdown into:
  - overview (everything before Week 1)
  - 6 week pages
  - wrap-up (everything from Course Wrap-Up onward)
Each page shares a sidebar menu, prev/next nav, and a language switcher.
"""

import re
import subprocess
from pathlib import Path
from html import escape

ROOT = Path("/tmp/ai-literacy")
OUT_BASE = ROOT / "reader"

# Map: lang_code -> (source_md_path, display_name_in_switcher,
#                    overview_label, week_label, wrapup_label, draft?)
LANGS = {
    "en": {
        "src": ROOT / "course" / "ai_literacy_course.md",
        "name": "English",
        "overview_label": "Course Overview",
        "week_word": "Week",
        "wrapup_label": "Course Wrap-Up",
        "prev_label": "← Previous",
        "next_label": "Next →",
        "back_label": "All languages",
        "subtitle": "A 6-week course for parents and teens",
        "draft": False,
    },
    "mi": {
        "src": ROOT / "translations" / "ai_literacy_course.mi.md",
        "name": "Te Reo Māori",
        "overview_label": "Tirohanga whānui o te Akoranga",
        "week_word": "Wiki",
        "wrapup_label": "Whakamutunga o te Akoranga",
        "prev_label": "← O mua",
        "next_label": "Muri →",
        "back_label": "Ngā reo katoa",
        "subtitle": "He akoranga 6-wiki mō ngā mātua me ngā taiohi",
        "draft": False,
    },
    "sm": {
        "src": ROOT / "translations" / "ai_literacy_course.sm.md",
        "name": "Gagana Sāmoa",
        "overview_label": "Va'aiga lautele",
        "week_word": "Vaiaso",
        "wrapup_label": "Fa'ai'uga o le A'oa'oga",
        "prev_label": "← Tua",
        "next_label": "Luma →",
        "back_label": "Gagana uma",
        "subtitle": "O se a'oa'oga 6-vaiaso mo mātua ma talavou",
        "draft": False,
    },
    "pt-BR": {
        "src": ROOT / "translations" / "ai_literacy_course.pt-BR.md",
        "name": "Português (Brasil)",
        "overview_label": "Visão Geral do Curso",
        "week_word": "Semana",
        "wrapup_label": "Encerramento do Curso",
        "prev_label": "← Anterior",
        "next_label": "Próximo →",
        "back_label": "Todos os idiomas",
        "subtitle": "Um curso de 6 semanas para pais e adolescentes",
        "draft": False,
    },
    "gn": {
        "src": ROOT / "translations" / "ai_literacy_course.gn.md",
        "name": "Avañe'ẽ / Guaraní",
        "overview_label": "Mbo'esyry Mba'éichapa Oĩ",
        "week_word": "Arapokõindy",
        "wrapup_label": "Mbo'esyry Ñemohu'ã",
        "prev_label": "← Tenondegua",
        "next_label": "Upei →",
        "back_label": "Opaite ñe'ẽ",
        "subtitle": "Peteĩ arandu 6 arapokõindy rehegua tuvakuérape ha mitãrusukuérape",
        "draft": True,
    },
    "pjt": {
        "src": ROOT / "translations" / "ai_literacy_course.pjt.md",
        "name": "Pitjantjatjara",
        "overview_label": "Course Overview",
        "week_word": "Week",
        "wrapup_label": "Course Wrap-Up",
        "prev_label": "← Previous",
        "next_label": "Next →",
        "back_label": "All languages",
        "subtitle": "Bilingual draft — Anangu review invited",
        "draft": True,
    },
}

LANG_ORDER = ["en", "mi", "sm", "pt-BR", "gn", "pjt"]


def md_to_html_fragment(md_text: str) -> str:
    """Convert markdown to an HTML fragment using pandoc (no <html>/<body> wrapper)."""
    result = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "html5", "--no-highlight"],
        input=md_text, capture_output=True, text=True, check=True,
    )
    return result.stdout


def split_course(md_text: str, cfg: dict):
    """Split a course markdown into ordered sections: overview, w1..w6, wrap."""
    lines = md_text.splitlines()
    # Find all ## headers and their line numbers
    headers = []  # list of (line_idx, level, title)
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            headers.append((i, len(m.group(1)), m.group(2).strip()))

    week_word = cfg["week_word"]
    wrapup_label = cfg["wrapup_label"]

    # Identify week section starts
    week_starts = {}  # week_num -> line_idx
    wrap_start = None
    overview_start = None

    for idx, (lineno, level, title) in enumerate(headers):
        if level != 2:
            continue
        # week match: ## <week_word> N  OR  ## Week N (English in PJT)
        wmatch = re.match(
            rf"^(?:{re.escape(week_word)}|Week)\s*(\d+)\b", title, re.IGNORECASE
        )
        if wmatch:
            n = int(wmatch.group(1))
            if n not in week_starts:
                week_starts[n] = lineno
            continue
        # wrap match
        if (
            title.lower().startswith(wrapup_label.lower())
            or "wrap" in title.lower()
            or "ñemohu'ã" in title.lower()
            or "whakamutunga" in title.lower()
            or "fa'ai'uga" in title.lower()
            or "encerramento" in title.lower()
        ):
            if wrap_start is None:
                wrap_start = lineno

    # overview is the first ## header before Week 1
    for lineno, level, title in headers:
        if level == 2:
            if week_starts and lineno < week_starts.get(1, 10**9):
                overview_start = lineno
                break
            else:
                # No earlier ##? overview is content above week 1
                overview_start = None
                break

    # Determine end indices
    ordered_starts = sorted(
        [(week_starts[n], f"w{n}") for n in week_starts]
        + ([(wrap_start, "wrap")] if wrap_start is not None else [])
    )

    sections = {}
    # overview: from overview_start (or top) to first week
    overview_end = ordered_starts[0][0] if ordered_starts else len(lines)
    overview_lines = lines[(overview_start or 0):overview_end]
    sections["overview"] = "\n".join(overview_lines).strip()

    # weeks + wrap
    for i, (start, key) in enumerate(ordered_starts):
        end = ordered_starts[i + 1][0] if i + 1 < len(ordered_starts) else len(lines)
        sections[key] = "\n".join(lines[start:end]).strip()

    return sections


CSS = """
:root {
  --ink: #111;
  --paper: #f8f5ee;
  --rule: #111;
  --accent: #b3000c;
  --muted: #5a5550;
  --soft: #efe9dc;
  --sidebar-bg: #efe9dc;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--paper);
  color: var(--ink);
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, "Times New Roman", serif;
  font-size: 17px;
  line-height: 1.55;
}

.layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 100vh;
}
@media (max-width: 880px) {
  .layout { grid-template-columns: 1fr; }
}

aside.sidebar {
  background: var(--sidebar-bg);
  border-right: 1px solid #d8d2c4;
  padding: 28px 22px 40px;
  position: sticky; top: 0;
  align-self: start;
  max-height: 100vh;
  overflow-y: auto;
}
@media (max-width: 880px) {
  aside.sidebar { position: static; max-height: none; }
}

.sidebar h2 {
  font-family: "Iowan Old Style", Georgia, serif;
  font-size: 20px;
  font-weight: 900;
  margin: 0 0 4px;
  letter-spacing: -0.01em;
}
.sidebar .subtitle {
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .1em;
  margin: 0 0 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid #c8bfa6;
}
.sidebar nav { margin-top: 12px; }
.sidebar nav h3 {
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .14em;
  color: var(--muted);
  margin: 18px 0 6px;
}
.sidebar nav ol, .sidebar nav ul {
  list-style: none;
  padding: 0; margin: 0;
}
.sidebar nav li { margin: 0; }
.sidebar nav a {
  display: block;
  padding: 7px 10px;
  text-decoration: none;
  color: var(--ink);
  font-size: 15px;
  border-left: 3px solid transparent;
}
.sidebar nav a:hover { background: rgba(0,0,0,0.04); }
.sidebar nav a.active {
  background: var(--paper);
  border-left-color: var(--accent);
  font-weight: 700;
}
.lang-switch select {
  width: 100%;
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 14px;
  padding: 6px 8px;
  background: var(--paper);
  border: 1px solid #c8bfa6;
}
.draft-pill {
  display: inline-block;
  background: #ffefcc;
  border: 1px solid #d6a700;
  color: #5a4400;
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .1em;
  padding: 2px 6px;
  margin-left: 6px;
  border-radius: 2px;
}

main.content {
  padding: 40px clamp(20px, 5vw, 60px) 80px;
  max-width: 820px;
}

main h1 {
  font-family: "Iowan Old Style", "Times New Roman", serif;
  font-weight: 900;
  font-size: clamp(30px, 4.5vw, 44px);
  line-height: 1.08;
  margin: 0 0 18px;
  letter-spacing: -0.01em;
  border-bottom: 2px solid var(--rule);
  padding-bottom: 10px;
}
main h2 {
  font-family: "Iowan Old Style", Georgia, serif;
  font-weight: 800;
  font-size: 26px;
  margin: 1.5em 0 0.4em;
  border-bottom: 1px solid #d8d2c4;
  padding-bottom: 4px;
}
main h3 {
  font-family: "Iowan Old Style", Georgia, serif;
  font-weight: 700;
  font-size: 20px;
  margin: 1.4em 0 0.3em;
}
main h4 {
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--muted);
  margin: 1.2em 0 0.2em;
}
main p { margin: 0.7em 0; }
main a { color: var(--accent); }
main ul, main ol { margin: 0.6em 0 0.6em 1.4em; }
main li { margin: 0.25em 0; }
main blockquote {
  border-left: 4px solid var(--accent);
  padding: 8px 14px;
  margin: 1em 0;
  background: rgba(0,0,0,0.03);
  font-style: italic;
  color: #333;
}
main hr { border: none; border-top: 1px solid #d8d2c4; margin: 1.6em 0; }
main code {
  font-family: "Iowan Old Style Mono", "Menlo", monospace;
  background: rgba(0,0,0,0.05);
  padding: 1px 5px;
  font-size: 0.95em;
}
main pre {
  background: #f0ece4;
  border: 1px solid #d8d2c4;
  padding: 12px 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.4;
}
main table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}
main th, main td {
  border: 1px solid #c8bfa6;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
  font-size: 15px;
}
main th { background: var(--soft); font-weight: 700; }

.pager {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid var(--rule);
  gap: 12px;
  flex-wrap: wrap;
}
.pager a {
  display: inline-block;
  padding: 10px 14px;
  background: var(--ink);
  color: var(--paper);
  text-decoration: none;
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: .1em;
  border: 2px solid var(--ink);
}
.pager a:hover { background: var(--accent); border-color: var(--accent); }
.pager a.outline { background: var(--paper); color: var(--ink); }
.pager a.outline:hover { color: white; }
.pager .placeholder { visibility: hidden; }

.crumbs {
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: .12em;
  color: var(--muted);
  margin-bottom: 6px;
}
.crumbs a { color: var(--muted); text-decoration: none; }
.crumbs a:hover { color: var(--accent); }

.footer-note {
  margin-top: 40px;
  padding-top: 16px;
  border-top: 1px solid #d8d2c4;
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 12px;
  color: var(--muted);
}
.footer-note a { color: var(--accent); }
"""


def page_filename(key: str) -> str:
    return {"overview": "index.html", "wrap": "wrap-up.html"}.get(key, f"{key}.html")


def build_sidebar(cfg: dict, current_key: str, lang_code: str, sections_present: list) -> str:
    week_word = cfg["week_word"]
    overview_label = cfg["overview_label"]
    wrapup_label = cfg["wrapup_label"]
    name = cfg["name"]
    subtitle = cfg["subtitle"]
    draft = cfg["draft"]

    nav_items = []
    if "overview" in sections_present:
        active = " class=\"active\"" if current_key == "overview" else ""
        nav_items.append(f'<li><a href="index.html"{active}>{escape(overview_label)}</a></li>')
    for n in range(1, 7):
        key = f"w{n}"
        if key in sections_present:
            active = " class=\"active\"" if current_key == key else ""
            nav_items.append(
                f'<li><a href="{key}.html"{active}>{escape(week_word)} {n}</a></li>'
            )
    if "wrap" in sections_present:
        active = " class=\"active\"" if current_key == "wrap" else ""
        nav_items.append(f'<li><a href="wrap-up.html"{active}>{escape(wrapup_label)}</a></li>')

    # Language switcher
    options = []
    for lc in LANG_ORDER:
        sel = " selected" if lc == lang_code else ""
        label = LANGS[lc]["name"]
        if LANGS[lc]["draft"]:
            label += " ⚠"
        options.append(f'<option value="../{lc}/{page_filename(current_key)}"{sel}>{escape(label)}</option>')

    draft_html = '<span class="draft-pill">working draft</span>' if draft else ""

    return f"""
<aside class="sidebar">
  <h2>AI Literacy {draft_html}</h2>
  <div class="subtitle">{escape(name)} · {escape(subtitle)}</div>
  <div class="lang-switch">
    <select onchange="if(this.value) window.location.href=this.value">
      {''.join(options)}
    </select>
  </div>
  <nav>
    <h3>Modules</h3>
    <ul>
      {''.join(nav_items)}
    </ul>
    <h3>Materials</h3>
    <ul>
      <li><a href="../../translations/pdf/ai_literacy_course.{lang_code}.pdf" target="_blank">Course PDF</a></li>
      <li><a href="../../translations/pdf/ai_literacy_workbook.{lang_code}.pdf" target="_blank">Workbook PDF</a></li>
      <li><a href="../../translations/pdf/ai_literacy_social_kit.{lang_code}.pdf" target="_blank">Social kit PDF</a></li>
    </ul>
    <h3>More</h3>
    <ul>
      <li><a href="../../index.html">← {escape(cfg['back_label'])}</a></li>
      <li><a href="https://kiwidialectic.substack.com" target="_blank">Substack</a></li>
      <li><a href="https://github.com/robertmccallnz/ai-literacy-for-families" target="_blank">GitHub</a></li>
    </ul>
  </nav>
</aside>
""".strip()


def build_pager(ordered_keys: list, current_key: str, cfg: dict) -> str:
    try:
        i = ordered_keys.index(current_key)
    except ValueError:
        return ""
    prev_html = '<span class="placeholder">·</span>'
    next_html = '<span class="placeholder">·</span>'
    if i > 0:
        prev_key = ordered_keys[i - 1]
        prev_html = f'<a class="outline" href="{page_filename(prev_key)}">{escape(cfg["prev_label"])}</a>'
    if i < len(ordered_keys) - 1:
        next_key = ordered_keys[i + 1]
        next_html = f'<a href="{page_filename(next_key)}">{escape(cfg["next_label"])}</a>'
    return f'<div class="pager">{prev_html}{next_html}</div>'


def build_page(lang_code: str, cfg: dict, key: str, body_html: str,
               ordered_keys: list, sections_present: list, title: str) -> str:
    sidebar = build_sidebar(cfg, key, lang_code, sections_present)
    pager = build_pager(ordered_keys, key, cfg)
    crumbs = f'<div class="crumbs"><a href="../../index.html">AI Literacy for Families</a> · {escape(cfg["name"])}</div>'
    return f"""<!doctype html>
<html lang="{lang_code}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — AI Literacy for Families</title>
<style>{CSS}</style>
</head>
<body>
<div class="layout">
{sidebar}
<main class="content">
{crumbs}
{body_html}
{pager}
<div class="footer-note">
  Free under CC BY-SA 4.0 · From <a href="https://kiwidialectic.substack.com">The Kiwi Dialectic</a> ·
  <a href="https://github.com/robertmccallnz/ai-literacy-for-families">Edit / translate / fork on GitHub</a>
</div>
</main>
</div>
</body>
</html>
"""


def main():
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    for lang_code, cfg in LANGS.items():
        src = cfg["src"]
        if not src.exists():
            print(f"SKIP {lang_code}: missing {src}")
            continue
        md_text = src.read_text(encoding="utf-8")
        sections = split_course(md_text, cfg)
        sections_present = [k for k in (["overview"] + [f"w{i}" for i in range(1, 7)] + ["wrap"]) if k in sections and sections[k].strip()]
        ordered_keys = sections_present.copy()

        out_dir = OUT_BASE / lang_code
        out_dir.mkdir(exist_ok=True)

        for key in sections_present:
            md_chunk = sections[key]
            body_html = md_to_html_fragment(md_chunk)
            # Find a title from first heading
            mt = re.match(r"^#+\s+(.*)$", md_chunk.lstrip().splitlines()[0]) if md_chunk.strip() else None
            title = mt.group(1) if mt else cfg["name"]
            page_html = build_page(lang_code, cfg, key, body_html,
                                   ordered_keys, sections_present, title)
            out_path = out_dir / page_filename(key)
            out_path.write_text(page_html, encoding="utf-8")
            print(f"  wrote {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
