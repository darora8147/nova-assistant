"""
server.py  (fixed)
------------------
FIX 1: /chat endpoint is now async (was sync - blocked all other requests).
FIX 2: /chat/stream endpoint added for token-by-token streaming responses.
FIX 3: Global exception handler returns JSON errors instead of crashing.
FIX 4: /health endpoint added to check Ollama status from the UI.
FIX 5: CORS enabled so frontend and backend can talk on different ports.
"""

import os
import asyncio
import json
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.assistant import chat, clear_session
from backend.router import get_mode, is_ollama_running, OFFLINE_MODEL, ONLINE_MODEL
from backend.memory import short_term, long_term

load_dotenv()

ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Nova")
USER_NAME      = os.getenv("USER_NAME", "Friend")

app = FastAPI(title=f"{ASSISTANT_NAME} – Personal AI Assistant")

# FIX: Allow requests from browser on same machine
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
STATIC_DIR   = os.path.join(FRONTEND_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# -- Models -------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


# -- Global error handler (FIX: was unhandled, caused 500 with no info) -------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"reply": f"Server error: {type(exc).__name__}: {exc}", "mode": get_mode()},
    )


# -- Routes -------------------------------------------------------------------

@app.get("/")
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    FIX: now async. Each request runs concurrently.
    Previous sync version blocked ALL requests while waiting for the LLM.
    """
    if not req.message.strip():
        return {"reply": "Please type something!", "mode": get_mode()}
    reply = await chat(req.message.strip())
    return {"reply": reply, "mode": get_mode()}


@app.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """
    FIX: Streaming endpoint - sends tokens as they arrive.
    The UI shows text word-by-word instead of waiting for the full response.
    This makes slow models feel MUCH faster.
    """
    if not req.message.strip():
        async def empty():
            yield f"data: {json.dumps({'token': 'Please type something!', 'done': True})}\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    async def token_generator():
        from backend.router import get_llm
        from backend.memory import short_term, long_term
        from backend.assistant import build_system_prompt
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        memories = long_term.search(req.message, n=2)
        system   = SystemMessage(content=build_system_prompt(memories))
        history  = [
            HumanMessage(content=m["content"]) if m["role"] == "user"
            else AIMessage(content=m["content"])
            for m in short_term.get_history()
        ]
        messages = [system] + history + [HumanMessage(content=req.message.strip())]

        full_reply = ""
        try:
            llm = get_llm()
            for chunk in llm.stream(messages):
                token = chunk.content
                if token:
                    full_reply += token
                    yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
                    await asyncio.sleep(0)   # yield control back to event loop
        except Exception as e:
            err = f"Error: {type(e).__name__}: {e}"
            yield f"data: {json.dumps({'token': err, 'done': True})}\n\n"
            return

        # Save to memory after full response
        short_term.add("user", req.message.strip())
        short_term.add("assistant", full_reply)
        long_term.save(req.message.strip(), full_reply)

        yield f"data: {json.dumps({'token': '', 'done': True, 'mode': get_mode()})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


@app.post("/clear")
async def clear_endpoint():
    clear_session()
    return {"status": "ok", "message": "Session cleared."}


@app.get("/status")
async def status_endpoint():
    ollama_ok = is_ollama_running()
    return {
        "mode": get_mode(),
        "assistant_name": ASSISTANT_NAME,
        "user_name": USER_NAME,
        "session_messages": len(short_term.get_history()),
        "total_memories": long_term.count(),
        "ollama_running": ollama_ok,
        "offline_model": OFFLINE_MODEL,
        "online_model": ONLINE_MODEL,
    }


@app.get("/history")
async def history_endpoint():
    return {"history": short_term.get_history()}


@app.get("/health")
async def health_endpoint():
    """Quick health check for the UI status bar."""
    return {"status": "ok", "mode": get_mode(), "ollama": is_ollama_running()}


@app.get("/sysinfo")
async def sysinfo_endpoint():
    """Return CPU and memory stats for the performance panel."""
    import shutil, platform
    info = {
        "platform": platform.system(),
        "cpu_count": os.cpu_count() or 1,
    }
    try:
        import psutil
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.2)
        info.update({
            "ram_total_gb": round(mem.total / 1e9, 1),
            "ram_used_gb":  round(mem.used  / 1e9, 1),
            "ram_pct":      mem.percent,
            "cpu_pct":      cpu,
        })
    except ImportError:
        info["error"] = "psutil not installed — run: pip install psutil"
    return info


# ── Job Agent Routes ──────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize DB and start job agent scheduler on server startup."""
    try:
        from job_agent.database import init_db
        init_db()
        from job_agent.job_agent import start_background_scheduler
        start_background_scheduler()
    except Exception as e:
        print(f"[job_agent] startup warning: {e}")


@app.post("/jobs/scrape")
async def jobs_scrape_now():
    """Trigger an immediate scrape (runs in background thread)."""
    import threading
    from job_agent.job_agent import run_scrape
    def _run():
        try: run_scrape()
        except Exception as e: print(f"[scrape] {e}")
    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "message": "Scraping started in background. Check /jobs/stats for progress."}


@app.post("/jobs/report")
async def jobs_send_report():
    """Send the daily email report now."""
    from job_agent.job_agent import run_report
    success = run_report()
    return {"status": "sent" if success else "failed"}


@app.get("/jobs/stats")
async def jobs_stats():
    """Return today's job stats."""
    from job_agent.database import get_stats_today
    return get_stats_today()


@app.get("/jobs/list")
async def jobs_list(min_score: int = 0, limit: int = 50, status: str = "found"):
    """Return jobs filtered by status (found / applied)."""
    from job_agent.database import get_conn
    with get_conn() as conn:
        if status == "applied":
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status='applied' ORDER BY applied_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM jobs
                   WHERE status != 'applied'
                   AND date(found_at) = date('now','localtime')
                   AND match_score >= ?
                   ORDER BY match_score DESC LIMIT ?""",
                (min_score, limit)
            ).fetchall()
        jobs = [dict(r) for r in rows]
    return {"jobs": jobs, "total": len(jobs)}


@app.get("/jobs/profile")
async def jobs_profile():
    """Return the current job profile."""
    import json
    from pathlib import Path
    p = Path("job_agent/profile.json")
    if p.exists():
        return json.loads(p.read_text())
    return {"error": "profile.json not found"}


class ApplyRequest(BaseModel):
    job_id: str


@app.post("/jobs/apply")
async def jobs_mark_applied(req: ApplyRequest):
    """Mark a job as applied."""
    from job_agent.database import update_status
    update_status(req.job_id, "applied")
    return {"status": "ok"}
