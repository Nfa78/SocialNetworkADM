from pathlib import Path
import html
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FILES = [
    DOCS / "elk_query_practice_5_questions.md",
    DOCS / "influxdb_flux_query_practice_5_questions.md",
    DOCS / "NEO4J_MODELING_QUESTIONS.md",
    DOCS / "NEO4J_QUERY_QUESTIONS.md",
    DOCS / "QUERY_QUESTIONS.md",
]
HTML_OUT = DOCS / "combined_exercises.html"
PDF_OUT = DOCS / "combined_exercises.pdf"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    output = []
    in_code = False
    code_lines = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip()

        if line.startswith("```"):
            close_list()
            if in_code:
                output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(raw)
            continue

        if not line.strip():
            close_list()
            output.append("")
        elif line.startswith("# "):
            close_list()
            output.append(f"<h1>{inline_markdown(line[2:])}</h1>")
        elif line.startswith("## "):
            close_list()
            output.append(f"<h2>{inline_markdown(line[3:])}</h2>")
        elif line.startswith("### "):
            close_list()
            output.append(f"<h3>{inline_markdown(line[4:])}</h3>")
        elif line.startswith("#### "):
            close_list()
            output.append(f"<h4>{inline_markdown(line[5:])}</h4>")
        elif line.startswith("> "):
            close_list()
            output.append(f"<blockquote>{inline_markdown(line[2:])}</blockquote>")
        elif line.strip() == "---":
            close_list()
            output.append("<hr>")
        elif line.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{inline_markdown(line[2:])}</li>")
        else:
            close_list()
            output.append(f"<p>{inline_markdown(line)}</p>")

    close_list()
    if in_code:
        output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")

    return "\n".join(output)


sections = []
for path in FILES:
    sections.append(
        f"""
        <section class="document">
          <div class="source-file">{html.escape(path.name)}</div>
          {markdown_to_html(path.read_text(encoding="utf-8"))}
        </section>
        """
    )

html_text = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Combined Exercises</title>
  <style>
    @page {{
      size: A4;
      margin: 18mm 16mm;
    }}
    body {{
      color: #1f2937;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      font-size: 11pt;
      line-height: 1.5;
    }}
    .cover {{
      break-after: page;
      padding-top: 80px;
    }}
    .cover h1 {{
      border: 0;
      font-size: 30pt;
      margin-bottom: 8px;
    }}
    .document {{
      break-before: page;
    }}
    .source-file {{
      color: #6b7280;
      font-size: 9pt;
      margin-bottom: 18px;
    }}
    h1, h2, h3 {{
      color: #111827;
      line-height: 1.25;
    }}
    h1 {{
      border-bottom: 1px solid #d1d5db;
      font-size: 22pt;
      margin: 0 0 18px;
      padding-bottom: 8px;
    }}
    h2 {{
      border-bottom: 1px solid #e5e7eb;
      font-size: 16pt;
      margin: 24px 0 10px;
      padding-bottom: 4px;
    }}
    h3 {{
      font-size: 13pt;
      margin: 18px 0 8px;
    }}
    h4 {{
      color: #111827;
      font-size: 11.5pt;
      margin: 15px 0 6px;
    }}
    p, ul, blockquote, pre {{
      margin: 0 0 11px;
    }}
    ul {{
      padding-left: 24px;
    }}
    blockquote {{
      border-left: 4px solid #cbd5e1;
      color: #475569;
      padding: 8px 12px;
      background: #f8fafc;
    }}
    code {{
      background: #f3f4f6;
      border-radius: 4px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.92em;
      padding: 1px 4px;
    }}
    pre {{
      background: #0f172a;
      border-radius: 6px;
      color: #e5e7eb;
      font-family: Consolas, "Courier New", monospace;
      font-size: 8.5pt;
      line-height: 1.35;
      overflow-wrap: anywhere;
      padding: 12px;
      white-space: pre-wrap;
    }}
    pre code {{
      background: transparent;
      color: inherit;
      padding: 0;
    }}
    hr {{
      border: 0;
      border-top: 1px solid #e5e7eb;
      margin: 20px 0;
    }}
  </style>
</head>
<body>
  <section class="cover">
    <h1>Combined Exercise Markdown Files</h1>
    <p>Generated from <code>./docs</code></p>
    <ul>
      {''.join(f'<li>{html.escape(path.name)}</li>' for path in FILES)}
    </ul>
  </section>
  {''.join(sections)}
</body>
</html>
"""

HTML_OUT.write_text(html_text, encoding="utf-8")

if not CHROME.exists():
    raise SystemExit(f"Chrome was not found at {CHROME}")

profile_dir = ROOT / ".tmp" / "chrome-pdf-profile"
profile_dir.mkdir(parents=True, exist_ok=True)
subprocess.run(
    [
        str(CHROME),
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={profile_dir}",
        f"--print-to-pdf={PDF_OUT}",
        HTML_OUT.resolve().as_uri(),
    ],
    check=True,
)
print(f"Wrote {PDF_OUT.relative_to(ROOT)} from {HTML_OUT.relative_to(ROOT)}")
