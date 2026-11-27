"""Parse uploaded files. CSV -> pandas tables. PDF/DOCX/TXT -> text chunks tagged with
file, document date, family (= file name without date), and location (page / section)."""
import os, re
import pandas as pd
from dateutil import parser as dparser
from pypdf import PdfReader
from docx import Document

TABLES = {}       # table name -> DataFrame
CHUNKS = []       # document chunks
DICT_TEXT = {}    # data-dictionary style text files (given to the table agent as context)
FILE_INFO = {}    # filename -> info for the UI

DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
DATE_LABEL = re.compile(r"(?:Document Date|Effective Date)\s*:\s*(.+)", re.I)
NUM_HEADING = re.compile(r"^\d+\.\s+\S")
MAX_CHUNK = 2000


def doc_date(text, filename):
    """Date from the document body label first, else from the file name. ISO string."""
    m = DATE_LABEL.search(text)
    if m:
        try:
            return dparser.parse(m.group(1).strip()).date().isoformat()
        except Exception:
            pass
    m = DATE_IN_NAME.search(filename)
    return m.group(1) if m else "0000-00-00"


def family(filename):
    stem = DATE_IN_NAME.sub("", os.path.splitext(filename)[0])
    return re.sub(r"[_\-\s]+$", "", stem).lower()


def _split_numbered(text, base):
    parts, title, cur = [], None, []
    for line in text.splitlines():
        if NUM_HEADING.match(line.strip()):
            if cur:
                parts.append((title, cur))
            title, cur = line.strip(), [line]
        else:
            cur.append(line)
    if cur:
        parts.append((title, cur))
    return [(f"{base}, section {t}" if t else base, "\n".join(c).strip())
            for t, c in parts if "\n".join(c).strip()]


def _read_pdf(path):
    out = []
    for i, page in enumerate(PdfReader(path).pages, 1):
        out += _split_numbered(page.extract_text() or "", f"page {i}")
    return out


def _read_docx(path):
    doc = Document(path)
    out, title, buf = [], "header", []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if p.style.name.lower().startswith(("heading", "title")):
            if buf:
                out.append((f"section {title}", "\n".join(buf)))
            title, buf = t, [t]
        else:
            buf.append(t)
    if buf:
        out.append((f"section {title}", "\n".join(buf)))
    for n, tb in enumerate(doc.tables, 1):
        rows = [" | ".join(c.text.strip() for c in r.cells) for r in tb.rows]
        out.append((f"table {n}", "\n".join(rows)))
    return out


def _read_txt(text):
    lines, out, title, buf, i = text.splitlines(), [], "header", [], 0
    while i < len(lines):
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if lines[i].strip() and len(nxt) >= 3 and set(nxt) <= set("-="):
            if buf:
                out.append((f"section {title}", "\n".join(buf)))
            title, buf, i = lines[i].strip(), [lines[i].strip()], i + 2
            continue
        buf.append(lines[i])
        i += 1
    if buf:
        out.append((f"section {title}", "\n".join(buf)))
    return out


def _cap(pieces):
    out = []
    for loc, text in pieces:
        text = text.strip()
        if not text:
            continue
        for k in range(0, len(text), MAX_CHUNK):
            suffix = f" (part {k // MAX_CHUNK + 1})" if len(text) > MAX_CHUNK else ""
            out.append((loc + suffix, text[k:k + MAX_CHUNK]))
    return out


def _parse_dates(df):
    """Columns whose every value looks like an ISO date become real datetimes, so the LLM never has to parse them."""
    for c in df.columns:
        if pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c]):
            vals = df[c].dropna().astype(str)
            if len(vals) and vals.str.match(r"^\d{4}-\d{2}-\d{2}").all():
                df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def ingest_file(path, filename):
    stem, ext = os.path.splitext(filename)
    ext = ext.lower()
    # forget old copy of the same file name
    TABLES.pop(stem, None) if ext == ".csv" else None
    CHUNKS[:] = [c for c in CHUNKS if c["file"] != filename]
    DICT_TEXT.pop(filename, None)

    if ext == ".csv":
        df = _parse_dates(pd.read_csv(path))
        TABLES[stem] = df
        FILE_INFO[filename] = {"name": filename, "kind": "table", "detail": f"{len(df)} rows, {len(df.columns)} cols"}
        return
    if ext in (".txt", ".md"):
        text = open(path, encoding="utf-8", errors="ignore").read()
        if "dictionary" in filename.lower():
            DICT_TEXT[filename] = text
            FILE_INFO[filename] = {"name": filename, "kind": "dictionary", "detail": "used as table context"}
            return
        pieces = _read_txt(text)
    elif ext == ".pdf":
        pieces = _read_pdf(path)
    elif ext == ".docx":
        pieces = _read_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    full = "\n".join(t for _, t in pieces)
    date = doc_date(full, filename)
    for loc, text in _cap(pieces):
        CHUNKS.append({"file": filename, "doc_date": date, "family": family(filename), "loc": loc, "text": text})
    FILE_INFO[filename] = {"name": filename, "kind": "document", "detail": f"dated {date}", "date": date}


def schema_text():
    parts = []
    for name, df in TABLES.items():
        cols = ", ".join(f"{c} ({t})" for c, t in df.dtypes.astype(str).items())
        sample = df.head(3).to_string(index=False)
        parts.append(f"TABLE {name} ({len(df)} rows)\nColumns: {cols}\nSample rows:\n{sample}")
    return "\n\n".join(parts)


def families():
    fam = {}
    for c in CHUNKS:
        fam.setdefault(c["family"], set()).add(c["doc_date"])
    return {f: sorted(d) for f, d in fam.items()}
