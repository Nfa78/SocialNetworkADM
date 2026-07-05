from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FILES = [
    DOCS / "elk_query_practice_5_questions.md",
    DOCS / "influxdb_flux_query_practice_5_questions.md",
    DOCS / "NEO4J_MODELING_QUESTIONS.md",
    DOCS / "NEO4J_QUERY_QUESTIONS.md",
    DOCS / "QUERY_QUESTIONS.md",
]
OUT = DOCS / "combined_exercises.pdf"

PAGE_W, PAGE_H = 612, 792
MARGIN_X, MARGIN_Y = 54, 54
LINE_H = 11.5
FONT_SIZE = 9
TITLE_SIZE = 16
SUBTITLE_SIZE = 12
MAX_CHARS = 92


def clean(text: str) -> str:
    table = str.maketrans(
        {
            "\u201c": '"',
            "\u201d": '"',
            "\u2018": "'",
            "\u2019": "'",
            "\u2013": "-",
            "\u2014": "-",
            "\u2026": "...",
            "\u00a0": " ",
            "\u2192": "->",
            "\u2265": ">=",
            "\u2264": "<=",
            "\u2260": "!=",
        }
    )
    return text.translate(table).encode("latin-1", "replace").decode("latin-1")


def pdf_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


pages = []
current = []
y = PAGE_H - MARGIN_Y


def new_page() -> None:
    global current, y
    if current:
        pages.append(current)
    current = []
    y = PAGE_H - MARGIN_Y


def add_line(text: str = "", font: str = "F1", size: int = FONT_SIZE, leading: float = LINE_H) -> None:
    global y
    if y < MARGIN_Y:
        new_page()
    current.append((MARGIN_X, y, font, size, text))
    y -= leading


def add_wrapped(
    text: str,
    font: str = "F1",
    size: int = FONT_SIZE,
    width: int = MAX_CHARS,
    leading: float = LINE_H,
) -> None:
    text = clean(text.rstrip())
    if not text:
        add_line("", font, size, leading)
        return
    wrapper = textwrap.TextWrapper(width=width, replace_whitespace=False, drop_whitespace=False)
    for part in wrapper.wrap(text) or [""]:
        add_line(part, font, size, leading)


add_line("Combined Exercise Markdown Files", "F2", TITLE_SIZE, 22)
add_line("Generated from ./docs", "F1", SUBTITLE_SIZE, 18)
add_line("", "F1", FONT_SIZE, 14)
for file_path in FILES:
    add_wrapped(f"- {file_path.name}", "F1", FONT_SIZE, 90)
new_page()

for index, path in enumerate(FILES):
    if index:
        new_page()
    add_line(path.name, "F2", TITLE_SIZE, 22)
    add_line("", "F1", FONT_SIZE, 12)
    in_code = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            in_code = not in_code
            add_wrapped(line, "F3", FONT_SIZE, 86)
            continue
        if in_code:
            add_wrapped(line.expandtabs(2), "F3", 8, 88, 10)
        elif line.startswith("# "):
            add_line("", "F1", FONT_SIZE, 8)
            add_wrapped(line[2:], "F2", 14, 70, 18)
        elif line.startswith("## "):
            add_line("", "F1", FONT_SIZE, 6)
            add_wrapped(line[3:], "F2", 12, 76, 15)
        elif line.startswith("### "):
            add_line("", "F1", FONT_SIZE, 4)
            add_wrapped(line[4:], "F2", 10, 82, 13)
        elif line.strip() == "---":
            add_line("-" * 76, "F1", FONT_SIZE, LINE_H)
        else:
            add_wrapped(line, "F1", FONT_SIZE, MAX_CHARS)

if current:
    pages.append(current)

objects = []


def add_obj(data: bytes) -> int:
    objects.append(data)
    return len(objects)


font1 = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
font2 = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
font3 = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
page_objs = []

for page in pages:
    stream_lines = ["BT"]
    last_font = None
    for x_pos, y_pos, font, size, text in page:
        font_ref = {"F1": font1, "F2": font2, "F3": font3}[font]
        del font_ref
        if last_font != (font, size):
            stream_lines.append(f"/{font} {size} Tf")
            last_font = (font, size)
        stream_lines.append(f"1 0 0 1 {x_pos:.2f} {y_pos:.2f} Tm ({pdf_escape(clean(text))}) Tj")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("latin-1", "replace")
    content = add_obj(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    page_obj = add_obj(
        f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
        f"/Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R /F3 {font3} 0 R >> >> "
        f"/Contents {content} 0 R >>".encode()
    )
    page_objs.append(page_obj)

pages_obj_num = len(objects) + 1
for page_obj in page_objs:
    objects[page_obj - 1] = objects[page_obj - 1].replace(b"/Parent 0 0 R", f"/Parent {pages_obj_num} 0 R".encode())

pages_obj = add_obj(f"<< /Type /Pages /Kids [{' '.join(f'{page} 0 R' for page in page_objs)}] /Count {len(page_objs)} >>".encode())
catalog_obj = add_obj(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())

pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
offsets = [0]
for index, obj in enumerate(objects, start=1):
    offsets.append(len(pdf))
    pdf.extend(f"{index} 0 obj\n".encode())
    pdf.extend(obj)
    pdf.extend(b"\nendobj\n")

xref_pos = len(pdf)
pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
pdf.extend(b"0000000000 65535 f \n")
for offset in offsets[1:]:
    pdf.extend(f"{offset:010d} 00000 n \n".encode())
pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())

OUT.write_bytes(pdf)
print(f"Wrote {OUT.relative_to(ROOT)} ({len(pages)} pages, {OUT.stat().st_size} bytes)")
