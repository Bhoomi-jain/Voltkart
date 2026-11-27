"""SQLite storage: chats, messages, uploaded-file registry. Survives restarts."""
import json, os, sqlite3, time

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER,
            role TEXT, content TEXT, ts REAL, citations TEXT, chart TEXT);
        CREATE TABLE IF NOT EXISTS files(name TEXT PRIMARY KEY, uploaded REAL);
        """)


def new_chat(title="New chat"):
    with _conn() as c:
        cur = c.execute("INSERT INTO chats(title, created) VALUES(?,?)", (title, time.time()))
        return cur.lastrowid


def list_chats():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM chats ORDER BY id DESC")]


def set_title(chat_id, title):
    with _conn() as c:
        c.execute("UPDATE chats SET title=? WHERE id=?", (title, chat_id))


def add_message(chat_id, role, content, citations=None, chart=None, ts=None):
    with _conn() as c:
        c.execute("INSERT INTO messages(chat_id, role, content, ts, citations, chart) VALUES(?,?,?,?,?,?)",
                  (chat_id, role, content, ts or time.time(),
                   json.dumps(citations or []), json.dumps(chart) if chart else None))


def messages(chat_id):
    with _conn() as c:
        rows = c.execute("SELECT * FROM messages WHERE chat_id=? ORDER BY id", (chat_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["citations"] = json.loads(d["citations"] or "[]")
        d["chart"] = json.loads(d["chart"]) if d["chart"] else None
        out.append(d)
    return out


def chat_exists(chat_id):
    with _conn() as c:
        return c.execute("SELECT 1 FROM chats WHERE id=?", (chat_id,)).fetchone() is not None


def register_file(name):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO files(name, uploaded) VALUES(?,?)", (name, time.time()))


def file_names():
    with _conn() as c:
        return [r["name"] for r in c.execute("SELECT name FROM files ORDER BY uploaded")]
