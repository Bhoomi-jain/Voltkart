"""Offline smoke test: no LLM needed (the LLM is replaced by a fake). Run from project root:
   python -m tests.smoke_test"""
import os, tempfile, shutil, re
from fastapi.testclient import TestClient
from backend import agent

def fake_llm(messages, json_mode=False, temperature=0):
    sys_, last = messages[0]["content"], messages[-1]["content"]
    if "router" in sys_:
        return '{"standalone_question":"x","use_tables":true,"use_docs":true,"chart":"bar","chart_title":"Revenue by category"}'
    if "pandas code" in sys_:
        return "```python\nm=order_items.merge(orders,on='order_id').merge(products,on='product_id')\nm=m[m.order_status=='Delivered']\nm['amt']=m.quantity*m.unit_price_inr*(1-m.discount_pct/100)\nresult=m.groupby('category',as_index=False).amt.sum().round(2)\n```"
    return "Total revenue by category is in the table [T1]. Return window per policy [D1]."
agent.llm = fake_llm

from backend.main import app
with TestClient(app) as c:
    b = "sample_bundle"
    files = [("files", (f, open(os.path.join(b, sub, f), "rb"))) for sub in ("tables", "documents") for f in os.listdir(os.path.join(b, sub))]
    files.append(("files", ("DATA_DICTIONARY.md", open(f"{b}/DATA_DICTIONARY.md", "rb"))))
    print(c.post("/api/files", files=files).json())
    for f in c.get("/api/files").json(): print(" ", f)
    cid = c.post("/api/chats").json()["id"]
    m = c.post(f"/api/chats/{cid}/messages", json={"content": "Show a bar chart"}).json()
    print(m["content"]); print("citations:", [x["id"] for x in m["citations"]], "chart:", m["chart"]["labels"] if m["chart"] else None)
    pdf = c.get(f"/api/chats/{cid}/export.pdf"); print("pdf bytes:", len(pdf.content), pdf.content[:4])
    print("doc retrieval:")
    for q in ["How soon must a customer report a product damaged on delivery?", "How much does VoltCare cost, and claim limit?", "ML engineer reports to whom, location, salary"]:
        print(" ", q); [print("    ", x["file"], x["doc_date"], x["loc"]) for x in agent.pick_docs(q)]
