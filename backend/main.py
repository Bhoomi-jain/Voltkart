from dotenv import load_dotenv
load_dotenv()  # must run before agent.py reads env vars

import os, time
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from . import agent, db, export, ingest

ROOT = os.path.join(os.path.dirname(__file__), "..")
UPLOADS = os.path.join(ROOT, "data", "uploads")
os.makedirs(UPLOADS, exist_ok=True)
ALLOWED = {".csv", ".pdf", ".docx", ".txt", ".md"}

app = FastAPI(title="VoltKart multi-source assistant")


@app.on_event("startup")
def startup():
    db.init()
    for name in db.file_names():  # reload files after restart
        p = os.path.join(UPLOADS, name)
        if os.path.exists(p):
            try:
                ingest.ingest_file(p, name)
            except Exception as e:
                print("could not reload", name, e)


@app.post("/api/files")
async def upload(files: list[UploadFile] = File(...)):
    ok, errors = [], []
    for f in files:
        name = os.path.basename(f.filename or "")
        if os.path.splitext(name)[1].lower() not in ALLOWED:
            errors.append(f"{name}: unsupported type")
            continue
        path = os.path.join(UPLOADS, name)
        with open(path, "wb") as out:
            out.write(await f.read())
        try:
            ingest.ingest_file(path, name)
            db.register_file(name)
            ok.append(name)
        except Exception as e:
            errors.append(f"{name}: {e}")
    return {"uploaded": ok, "errors": errors}


@app.get("/api/files")
def list_files():
    return [ingest.FILE_INFO[n] for n in db.file_names() if n in ingest.FILE_INFO]


@app.post("/api/chats")
def create_chat():
    return {"id": db.new_chat()}


@app.get("/api/chats")
def chats():
    return db.list_chats()


@app.get("/api/chats/{cid}/messages")
def get_messages(cid: int):
    return db.messages(cid)


@app.post("/api/chats/{cid}/messages")
def send(cid: int, body: dict):
    if not db.chat_exists(cid):
        raise HTTPException(404, "chat not found")
    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(400, "empty message")
    ts = time.time()
    history = db.messages(cid)  # only THIS chat -> no leakage between chats
    try:
        res = agent.answer(content, history)
    except Exception as e:
        raise HTTPException(502, f"LLM/pipeline error: {e}")
    db.add_message(cid, "user", content, ts=ts)
    db.add_message(cid, "assistant", res["content"], res["citations"], res["chart"])
    if not history:
        db.set_title(cid, content[:40])
    return db.messages(cid)[-1]


@app.get("/api/chats/{cid}/export.pdf")
def export_pdf(cid: int):
    title = next((c["title"] for c in db.list_chats() if c["id"] == cid), "Chat")
    pdf = export.build_pdf(f"VoltKart chat export: {title}", db.messages(cid))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=chat{cid}.pdf"})


app.mount("/", StaticFiles(directory=os.path.join(ROOT, "frontend"), html=True), name="frontend")
