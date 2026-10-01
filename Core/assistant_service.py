"""Shared, serialized assistant entry point for dashboard and voice clients."""
from pathlib import Path
import json, sqlite3, threading, uuid
from datetime import datetime, timezone

_lock = threading.RLock()
DB = Path(__file__).resolve().parents[1] / "Data/assistant_runs.db"

def _db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS runs(
      id TEXT PRIMARY KEY, request TEXT NOT NULL, status TEXT NOT NULL,
      reply TEXT, created_at TEXT NOT NULL, finished_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS run_steps(
      id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, tool TEXT NOT NULL,
      arguments TEXT NOT NULL, status TEXT NOT NULL, evidence TEXT,
      started_at TEXT NOT NULL, finished_at TEXT)""")
    return c

def ask(request, request_id=None, ask_fn=None):
    if ask_fn is None:
        raise ValueError('Supply a reviewed handler; the full Penny brain is not bundled here')
    if not isinstance(request, str) or not request.strip():
        raise ValueError("A request is required")
    rid = request_id or str(uuid.uuid4())
    with _lock:
        c = _db()
        # Claim the ID atomically across processes before any handler can run.
        c.execute('BEGIN IMMEDIATE')
        row = c.execute("SELECT id, status, reply, request FROM runs WHERE id=?", (rid,)).fetchone()
        if row and row[3] != request.strip():
            c.close()
            raise ValueError('Request ID already belongs to a different request')
        if row and row[1] == "completed":
            c.close(); return {"request_id": rid, "status": row[1], "reply": row[2], "replayed": True}
        if row:
            c.close()
            return {'request_id': rid, 'status': row[1], 'reply': row[2] or 'This request has an uncertain outcome. Check its result before submitting a new action.', 'replayed': True}
        now = datetime.now(timezone.utc).isoformat()
        c.execute("INSERT INTO runs(id,request,status,created_at) VALUES(?,?,?,?)", (rid, request.strip(), "running", now)); c.commit()
        from Core.execution_trace import current
        def begin(tool, arguments):
            cursor = c.execute('INSERT INTO run_steps(run_id,tool,arguments,status,started_at) VALUES(?,?,?,?,?)',
                               (rid, tool, json.dumps(arguments), 'started', datetime.now(timezone.utc).isoformat()))
            c.commit()
            return cursor.lastrowid
        def finish(step_id, status, evidence):
            c.execute('UPDATE run_steps SET status=?,evidence=?,finished_at=? WHERE id=? AND run_id=?',
                      (status, json.dumps(evidence), datetime.now(timezone.utc).isoformat(), step_id, rid))
            c.commit()
        trace = {'status': 'responded', 'begin': begin, 'finish': finish}
        token = current.set(trace)
        try:
            state = c.execute("SELECT status FROM runs WHERE id=?", (rid,)).fetchone()
            if state and state[0] == "cancel_requested":
                return {"request_id": rid, "status": "cancelled", "reply": "Penny cancelled the request before it started.", "replayed": False}
            reply = str(ask_fn(request.strip()))
            finished = datetime.now(timezone.utc).isoformat()
            c.execute("UPDATE runs SET status=?, reply=?, finished_at=? WHERE id=?", (trace['status'], reply, finished, rid)); c.commit()
            return {"request_id": rid, "status": trace['status'], "reply": reply, "replayed": False}
        except Exception as exc:
            c.execute("UPDATE runs SET status='failed', reply=?, finished_at=? WHERE id=?", (f"Penny could not complete this request: {exc}", datetime.now(timezone.utc).isoformat(), rid)); c.commit()
            raise
        finally:
            current.reset(token)
            c.close()

def get_run(request_id):
    c = _db()
    try:
        r = c.execute("SELECT id,request,status,reply,created_at,finished_at FROM runs WHERE id=?", (request_id,)).fetchone()
        if not r:
            return None
        result = dict(zip(("request_id","request","status","reply","created_at","finished_at"), r))
        steps = c.execute('SELECT id,tool,arguments,status,evidence,started_at,finished_at FROM run_steps WHERE run_id=? ORDER BY id', (request_id,)).fetchall()
        result['steps'] = [dict(zip(('id','tool','arguments','status','evidence','started_at','finished_at'), step)) for step in steps]
        for step in result['steps']:
            step['arguments'] = json.loads(step['arguments'])
            step['evidence'] = json.loads(step['evidence']) if step['evidence'] else None
        return result
    finally: c.close()

def cancel_run(request_id):
    """Request cancellation before a queued run starts; never pretends to undo actions."""
    # Do not wait behind an executing request and then claim it was cancelled.
    result = get_run(request_id)
    if result is None:
        return None
    return {**result, 'cancelled': False, 'reason': 'In-flight cancellation is not supported. Already sent actions cannot be undone here.'}

def recent_runs(limit=20):
    limit = max(1, min(int(limit), 100))
    c = _db()
    try:
        rows = c.execute("SELECT id,request,status,reply,created_at,finished_at FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        keys = ("request_id", "request", "status", "reply", "created_at", "finished_at")
        return [dict(zip(keys, row)) for row in rows]
    finally: c.close()
