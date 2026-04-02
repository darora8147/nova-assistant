"""
memory.py  (fixed)
------------------
FIX 1: ChromaDB is fully lazy - initialised only on first actual use.
FIX 2: long_term.save() is non-blocking (errors are swallowed, not raised).
FIX 3: long_term.search() returns [] on any failure instead of crashing.
FIX 4: LongTermMemory is fully optional - app works fine without it.
"""

import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MEMORY_WINDOW = int(os.getenv("MEMORY_WINDOW", 20))
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "memory_db")


# -- Short-term (in-memory session history) -----------------------------------

class ShortTermMemory:
    def __init__(self, window: int = MEMORY_WINDOW):
        self.window = window
        self.messages: list[dict] = []

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.window * 2:
            self.messages = self.messages[-(self.window * 2):]

    def get_history(self) -> list[dict]:
        return self.messages.copy()

    def clear(self):
        self.messages = []


# -- Long-term (ChromaDB vector store on disk) --------------------------------

class LongTermMemory:
    def __init__(self):
        self._collection = None
        self._failed = False   # FIX: if init fails once, stop retrying

    def _get_collection(self):
        """Lazy-load ChromaDB. Mark as failed if unavailable."""
        if self._failed:
            return None
        if self._collection is None:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=DB_PATH)
                self._collection = client.get_or_create_collection(
                    name="conversations",
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                print(f"[memory] ChromaDB unavailable: {e}. Long-term memory disabled.")
                self._failed = True
                return None
        return self._collection

    def save(self, user_msg: str, bot_msg: str):
        """Save silently - never raise, never block the response."""
        try:
            col = self._get_collection()
            if col is None:
                return
            col.add(
                ids=[str(uuid.uuid4())],
                documents=[f"User: {user_msg}\nAssistant: {bot_msg}"],
                metadatas=[{
                    "timestamp": datetime.now().isoformat(),
                    "user": user_msg[:500],
                    "bot": bot_msg[:500],
                }],
            )
        except Exception:
            pass   # FIX: never crash the chat on a memory write failure

    def search(self, query: str, n: int = 3) -> list[str]:
        """Return N most relevant past exchanges, or [] on any error."""
        try:
            col = self._get_collection()
            if col is None or col.count() == 0:
                return []
            results = col.query(
                query_texts=[query],
                n_results=min(n, col.count()),
            )
            return results["documents"][0] if results["documents"] else []
        except Exception:
            return []

    def count(self) -> int:
        try:
            col = self._get_collection()
            return col.count() if col else 0
        except Exception:
            return 0


# -- Global singletons --------------------------------------------------------

short_term = ShortTermMemory()
long_term  = LongTermMemory()
