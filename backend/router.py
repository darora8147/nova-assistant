"""
router.py  (performance tuned)
-------------------------------
Key changes:
- Reads OLLAMA_NUM_CTX and OLLAMA_NUM_THREAD from .env
- LLM instance cached globally — never re-created per request
- Ollama health check is quick (3s timeout)
- is_online() uses a fast DNS probe with 2s timeout
"""

import os
import socket
import httpx
from dotenv import load_dotenv

load_dotenv()

OFFLINE_MODEL    = os.getenv("OFFLINE_MODEL",     "phi3:mini")
ONLINE_MODEL     = os.getenv("ONLINE_MODEL",      "gpt-4o-mini")
OPENAI_KEY       = os.getenv("OPENAI_API_KEY",    "")
OLLAMA_NUM_CTX   = int(os.getenv("OLLAMA_NUM_CTX",    "1024"))
OLLAMA_NUM_THREAD= int(os.getenv("OLLAMA_NUM_THREAD",  "4"))
LLM_TIMEOUT      = int(os.getenv("LLM_TIMEOUT",       "120"))

_llm_cache = None


def is_online() -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(("8.8.8.8", 53))
        return True
    except OSError:
        return False


def is_ollama_running() -> bool:
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def get_mode() -> str:
    return "online" if (is_online() and OPENAI_KEY) else "offline"


def get_llm(force_refresh: bool = False):
    global _llm_cache
    if _llm_cache is not None and not force_refresh:
        return _llm_cache

    if get_mode() == "online":
        from langchain_openai import ChatOpenAI
        _llm_cache = ChatOpenAI(
            model=ONLINE_MODEL,
            openai_api_key=OPENAI_KEY,
            temperature=0.7,
            streaming=True,
            request_timeout=60,
        )
    else:
        if not is_ollama_running():
            raise RuntimeError(
                "Ollama is not running.\n"
                "Fix: open a NEW terminal and run:  ollama serve\n"
                "Then refresh this page."
            )
        from langchain_community.chat_models import ChatOllama
        _llm_cache = ChatOllama(
            model=OFFLINE_MODEL,
            temperature=0.7,
            num_ctx=OLLAMA_NUM_CTX,       # from .env — lower = less RAM
            num_thread=OLLAMA_NUM_THREAD, # from .env — limit CPU thrashing
            num_gpu=0,                    # set to 1 if you have a GPU
            repeat_penalty=1.1,           # reduces repetitive outputs
            top_k=40,
            top_p=0.9,
        )

    return _llm_cache
