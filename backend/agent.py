"""The AI pipeline:  router -> (table agent) + (document retrieval) -> final answer with citations.
LLM is any OpenAI-compatible endpoint (Ollama by default; Groq / Gemini / OpenAI by changing .env)."""
import json, logging, os, re
import pandas as pd
from openai import OpenAI
from . import ingest

os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
logging.basicConfig(filename=os.path.join(os.path.dirname(__file__), "..", "data", "debug.log"),
                    level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("agent")

client = OpenAI(base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
                api_key=os.getenv("LLM_API_KEY", "ollama"))
MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")

DEFAULT_DEFINITIONS = (
    "Default business definitions (used only if no data dictionary was uploaded): "
    "line amount = quantity * unit_price * (1 - discount_pct/100); revenue = sum of line amounts "
    "for orders whose status is Delivered (cancelled orders are not revenue)."
)


def llm(messages, json_mode=False, temperature=0):
    kw = {"response_format": {"type": "json_object"}} if json_mode else {}
    r = client.chat.completions.create(model=MODEL, messages=messages, temperature=temperature, **kw)
    return r.choices[0].message.content or ""


def _json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


def _strip_cites(s):
    return re.sub(r"\s*\[[TD]\d+(?:\s*,\s*[TD]\d+)*\]", "", s)


# ---------------------------------------------------------------- router
def route(question, history):
    hist = "\n".join(f"{m['role']}: {_strip_cites(m['content'])[:600]}" for m in history[-6:])
    fams = "; ".join(f"{f} (versions {', '.join(d)})" for f, d in ingest.families().items()) or "none"
    system = (
        "You are a router for a chat assistant. Return ONLY JSON with keys:\n"
        '"standalone_question": rewrite the latest user message as a complete self-contained question, '
        'resolving references like "that store", "the second one", "it" using the chat history;\n'
        '"use_tables": true if answering needs numbers/records from the CSV tables;\n'
        '"use_docs": true if it needs text documents (policies, job descriptions, warranty, notices);\n'
        '"chart": "bar" | "line" | "pie" | null (only if the user asks for a chart/graph/plot);\n'
        '"chart_title": short chart title or null.\n'
        "Both use_tables and use_docs can be true (e.g. a customer's order checked against a policy). "
        "If the question is only about the conversation itself (e.g. summarize what we discussed), set both false.\n"
        f"Available tables: {', '.join(ingest.TABLES) or 'none'}\nAvailable document families: {fams}"
    )
    try:
        d = _json(llm([{"role": "system", "content": system},
                       {"role": "user", "content": f"Chat history:\n{hist or '(empty)'}\n\nLatest message: {question}"}],
                      json_mode=True))
    except Exception:
        d = {}
    return {
        "q": d.get("standalone_question") or question,
        "tables": bool(d.get("use_tables", bool(ingest.TABLES))) and bool(ingest.TABLES),
        "docs": bool(d.get("use_docs", bool(ingest.CHUNKS))) and bool(ingest.CHUNKS),
        "chart": d.get("chart") if d.get("chart") in ("bar", "line", "pie") else None,
        "chart_title": d.get("chart_title"),
    }


# ---------------------------------------------------------------- tables
SAFE_BUILTINS = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k)
                 for k in ("len", "sum", "min", "max", "round", "sorted", "list", "dict", "set", "str", "int",
                           "float", "abs", "range", "zip", "enumerate", "any", "all", "isinstance", "tuple", "bool",
                           "print", "map", "filter", "reversed")}


def run_code(code):
    g = {"__builtins__": SAFE_BUILTINS, "pd": pd}
    for name, df in ingest.TABLES.items():
        g[name] = df.copy()
    exec(code, g)
    if g.get("result") is None:
        raise ValueError("code did not assign a value to `result`")
    res = g["result"]
    if isinstance(res, (pd.DataFrame, pd.Series)) and len(res) == 0:
        raise ValueError("result is EMPTY. Check your filters: dates are already datetime64 (use .dt.year == 2025 with an "
                         "integer, .dt.month, or comparisons with pd.Timestamp), and check status/category spellings.")
    return res


def _extract_code(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def table_agent(question, chart):
    dictionary = "\n\n".join(ingest.DICT_TEXT.values()) or DEFAULT_DEFINITIONS
    system = (
        "You write pandas code to answer a question over CSV tables that are ALREADY loaded as DataFrames, "
        f"each named exactly like its table: {', '.join(ingest.TABLES)}.\n"
        "Rules: no imports, no print, no file access. Join with .merge() on the key columns. "
        "Columns shown as datetime64 are ALREADY real dates: do NOT call pd.to_datetime on them or pass a format; "
        "use .dt.year == 2025 (integer), .dt.month, .dt.quarter, or compare with pd.Timestamp('2026-01-01'). "
        "Pattern for revenue: df['amount'] = df.quantity * df.unit_price_inr * (1 - df.discount_pct/100); "
        "filter to delivered orders; then groupby(...)['amount'].sum().reset_index(). "
        "Assign the final answer to a variable named `result` (a DataFrame, Series or scalar). "
        "Include every column the question asks for (e.g. names AND ids, store AND manager). "
        "Do not shorten lists: if asked to name items, return all of them. Round money to 2 decimals. "
        "Follow the business definitions exactly. Return ONLY one ```python code block.\n"
        + ("The result must be a DataFrame with exactly two columns: first the label, then the numeric value, "
           "in a sensible order (chronological for line charts).\n" if chart else "")
        + f"\n=== Business definitions / data dictionary ===\n{dictionary}\n\n=== Tables ===\n{ingest.schema_text()}"
    )
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    last_err, code = "", ""
    for _ in range(3):
        code = _extract_code(llm(msgs, temperature=0 if _ == 0 else 0.4))
        try:
            res = run_code(code)
            log.info("TABLE OK attempt=%s q=%s\n%s", _ + 1, question, code)
            return code, res, None
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            log.info("TABLE FAIL attempt=%s q=%s err=%s\n%s", _ + 1, question, last_err, code)
            msgs += [{"role": "assistant", "content": f"```python\n{code}\n```"},
                     {"role": "user", "content": f"That code failed with: {last_err}\nTry a DIFFERENT, simpler approach (build the result step by step) and return the full corrected code."}]
    return code, None, last_err


def result_to_text(res):
    if isinstance(res, pd.Series):
        res = res.reset_index()
    if isinstance(res, pd.DataFrame):
        extra = f"\n(showing first 50 of {len(res)} rows)" if len(res) > 50 else ""
        return res.head(50).to_markdown(index=False, floatfmt=".2f") + extra, res
    return str(res), None


# ---------------------------------------------------------------- documents
STOP = set("a an the of to in on for is are was were be by with and or what which who how many much does do did "
           "it its that this these those at as from about me my we our their his her will would can could should "
           "there than then them they you your has have had not".split())


def _toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2}


def pick_docs(question, k=2):
    """Pick the best-matching document families (IDF-weighted word overlap, family-name words count extra),
    return ALL versions of them, newest first inside each family."""
    import math
    fam = {}
    for c in ingest.CHUNKS:
        fam.setdefault(c["family"], []).append(c)
    if not fam:
        return []
    q = _toks(question)
    words = {f: _toks(" ".join(c["text"] for c in cs)) for f, cs in fam.items()}
    names = {f: _toks(f.replace("_", " ")) for f in fam}
    n = len(fam)
    scores = {}
    for f in fam:
        s = 0.0
        for w in q:
            df = sum(1 for g in fam if w in words[g] or w in names[g])
            idf = math.log(1 + n / df) if df else 0
            if w in words[f]:
                s += idf
            if w in names[f]:
                s += 3 * idf
        scores[f] = s
    ranked = sorted(scores, key=scores.get, reverse=True)
    top = scores[ranked[0]]
    chosen = [f for f in ranked[:k] if scores[f] > 0 and scores[f] >= 0.6 * top]
    chunks = [c for f in chosen for c in fam[f]]
    chunks.sort(key=lambda c: (c["family"], c["doc_date"]), reverse=True)
    return chunks


# ---------------------------------------------------------------- main entry
ANSWER_RULES = (
    "You are VoltKart's data assistant. Answer ONLY from the SOURCES below and the chat history.\n"
    "- After EVERY fact, add its source tag in square brackets, e.g. [T1] or [D2]. Never invent tags.\n"
    "- Table numbers: copy them from the table results; do not recompute or estimate. Show money as INR.\n"
    "- Documents come in several dated versions, listed NEWEST FIRST. For each fact use the newest version that "
    "explicitly states it. If a fact appears only in an older version, still answer from it but say clearly which "
    "version (its date) it comes from. If versions conflict, the newest wins; you may mention the change briefly.\n"
    "- If the sources do not contain the answer, say you could not find it in the provided files. Never guess.\n"
    "- If a table query FAILED, say so; do not make up numbers.\n"
    "- Questions about the conversation itself (e.g. summaries) are answered from the chat history, no tags needed.\n"
    "- When combining a table fact and a policy, state each step (e.g. tier -> window -> decision).\n"
    "- Use markdown (tables allowed). Be concise."
)


def answer(question, history):
    r = route(question, history)
    log.info("ROUTE %s", r)
    ctx, cmap, chart = [], {}, None

    if r["tables"]:
        code, res, err = table_agent(r["q"], r["chart"])
        if err:
            ctx.append(f"[T1] TABLE QUERY FAILED after retries: {err}")
            cmap["T1"] = {"id": "T1", "type": "table", "tables": [t for t in ingest.TABLES if re.search(rf"\b{re.escape(t)}\b", code)],
                          "code": code, "result": f"FAILED: {err}", "question": r["q"]}
        else:
            text, df = result_to_text(res)
            used = [t for t in ingest.TABLES if re.search(rf"\b{re.escape(t)}\b", code)]
            cmap["T1"] = {"id": "T1", "type": "table", "tables": used, "code": code, "result": text, "question": r["q"]}
            ctx.append(f"[T1] Table query (tables: {', '.join(used)}). Question: {r['q']}\nResult:\n{text}")
            if r["chart"] and df is not None and df.shape[1] >= 2:
                vals = pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0).tolist()
                chart = {"type": r["chart"], "title": r["chart_title"] or r["q"],
                         "x_label": str(df.columns[0]), "y_label": str(df.columns[1]),
                         "labels": df.iloc[:, 0].astype(str).tolist(), "values": vals}

    if r["docs"]:
        for i, c in enumerate(pick_docs(r["q"]), 1):
            key = f"D{i}"
            cmap[key] = {"id": key, "type": "document", "file": c["file"], "date": c["doc_date"],
                         "location": c["loc"], "text": c["text"][:400]}
            ctx.append(f"[{key}] file={c['file']} | document date={c['doc_date']} | {c['loc']}\n{c['text']}")

    msgs = [{"role": "system", "content": ANSWER_RULES}]
    msgs += [{"role": m["role"], "content": _strip_cites(m["content"])} for m in history[-8:]]
    sources = "\n\n".join(ctx) if ctx else "(no sources used for this question)"
    msgs.append({"role": "user", "content": f"SOURCES:\n{sources}\n\nQUESTION: {r['q']}"})
    text = llm(msgs)

    cited = []
    for grp in re.findall(r"\[([^\]]+)\]", text):
        cited += re.findall(r"[TD]\d+", grp)
    keys = [k for k in dict.fromkeys(cited) if k in cmap]
    if chart and "T1" in cmap and "T1" not in keys:
        keys.insert(0, "T1")
    if not keys and cmap and (r["tables"] or r["docs"]):
        keys = list(cmap)  # model forgot tags: show everything that was consulted
    return {"content": text, "citations": [cmap[k] for k in keys], "chart": chart}
