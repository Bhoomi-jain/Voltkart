"""Chat -> PDF (reportlab). Messages in order with timestamps, citations under each answer, charts as images."""
import html, io, re, time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image


def _clean(s):
    s = (s or "").replace("\u20b9", "Rs.").replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return s.encode("latin-1", "replace").decode("latin-1")


def _md(s):
    s = html.escape(_clean(s))
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s.replace("\n", "<br/>")


def _chart_png(ch):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    if ch["type"] == "pie":
        ax.pie(ch["values"], labels=ch["labels"], autopct="%1.1f%%")
    elif ch["type"] == "line":
        ax.plot(ch["labels"], ch["values"], marker="o")
        ax.set_xlabel(_clean(ch["x_label"])); ax.set_ylabel(_clean(ch["y_label"]))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    else:
        ax.bar(ch["labels"], ch["values"])
        ax.set_xlabel(_clean(ch["x_label"])); ax.set_ylabel(_clean(ch["y_label"]))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    ax.set_title(_clean(ch["title"]), fontsize=10)
    fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=150); plt.close(fig); buf.seek(0)
    return buf


def build_pdf(title, messages):
    ss = getSampleStyleSheet()
    code = ParagraphStyle("c", parent=ss["Code"], fontSize=7, leading=9)
    small = ParagraphStyle("s", parent=ss["Normal"], fontSize=8, textColor="#555555")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = [Paragraph(_md(title), ss["Title"]), Spacer(1, 8)]
    for m in messages:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(m["ts"]))
        who = "User" if m["role"] == "user" else "Assistant"
        story += [Paragraph(f"<b>{who}</b> - {stamp}", ss["Heading4"]), Paragraph(_md(m["content"]), ss["Normal"])]
        if m.get("chart"):
            story += [Spacer(1, 6), Image(_chart_png(m["chart"]), width=14*cm, height=7.5*cm)]
        if m["role"] == "assistant" and m.get("citations"):
            story.append(Paragraph("<b>Citations</b>", small))
            for c in m["citations"]:
                if c["type"] == "document":
                    story.append(Paragraph(_md(f"[{c['id']}] {c['file']} | document date {c['date']} | {c['location']}"), small))
                else:
                    story.append(Paragraph(_md(f"[{c['id']}] Tables used: {', '.join(c['tables'])}. Query:"), small))
                    story.append(Paragraph(_md(c["code"]).replace(" ", "&nbsp;"), code))
        story.append(Spacer(1, 10))
    doc.build(story)
    return buf.getvalue()
