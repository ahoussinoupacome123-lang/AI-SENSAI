"""External Structured Memory / Second Brain (feature M3 - 2 stars).
Allows Sensai to index, recall, and search facts across multiple conversation sessions.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Callable, Optional

import numpy as np

from src import store

ROOT = Path(__file__).resolve().parent.parent

RECALL_PATTERNS = [
    re.compile(r"\b(remember|recall|earlier|previous\s+session|previous\s+conversation|last\s+time|we\s+discussed|past\s+discussion)\b", re.IGNORECASE),
    re.compile(r"\b(rappelle|souviens|conversation\s+pr[eé]c[eé]dente|autre\s+session|on\s+a\s+dit|discut[eé]\s+hier)\b", re.IGNORECASE),
    re.compile(r"\b(what\s+did\s+we\s+(talk|say|discuss)\s+about)\b", re.IGNORECASE),
    re.compile(r"\b(de\s+quoi\s+(parlait-on|avons-nous\s+parl[eé]))\b", re.IGNORECASE),
]


class SessionMemory:
    """Manages cross-session conversation persistence, indexing, and semantic recall."""

    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
        embed_model: str = "nomic-embed-text",
        host: str = "http://localhost:11434",
        embed_fn: Optional[Callable[[list[str], str], list[list[float]]]] = None,
    ):
        self.base_dir = Path(base_dir) if base_dir else ROOT / ".sensai"
        self.sessions_dir = self.base_dir / "sessions"
        self.index_path = self.base_dir / "memory_index.json"
        self.embed_model = embed_model
        self.host = host
        self.embed_fn = embed_fn
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save_session(
        self,
        session_id: str,
        turns: list[dict],
        title: str = "Chat Session",
        metadata: Optional[dict] = None,
    ) -> Path:
        """Persist a conversation session to disk as JSON."""
        safe_id = re.sub(r"[^\w\-]", "_", session_id)
        file_path = self.sessions_dir / f"{safe_id}.json"
        clean_turns = [
            {"role": t.get("role", "user"), "content": str(t.get("content") or t.get("text") or "").strip()}
            for t in turns
            if t.get("role") in ("user", "assistant", "bot") and (t.get("content") or t.get("text"))
        ]
        # Standardize bot -> assistant
        for t in clean_turns:
            if t["role"] == "bot":
                t["role"] = "assistant"

        data = {
            "id": safe_id,
            "title": title or "Chat Session",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn_count": len(clean_turns),
            "metadata": metadata or {},
            "turns": clean_turns,
        }
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return file_path

    def load_session(self, session_id: str) -> dict:
        """Load a persisted session by ID."""
        safe_id = re.sub(r"[^\w\-]", "_", session_id)
        file_path = self.sessions_dir / f"{safe_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Session file not found: {file_path}")
        return json.loads(file_path.read_text())

    def list_sessions(self) -> list[dict]:
        """List summary metadata of all saved sessions."""
        sessions = []
        for p in sorted(self.sessions_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                data = json.loads(p.read_text())
                sessions.append({
                    "id": data.get("id", p.stem),
                    "title": data.get("title", "Untitled"),
                    "timestamp": data.get("timestamp", ""),
                    "turn_count": data.get("turn_count", len(data.get("turns", []))),
                    "path": str(p),
                })
            except Exception:
                continue
        return sessions

    def index_sessions(
        self,
        embed_fn: Optional[Callable[[list[str], str], list[list[float]]]] = None,
    ) -> list[dict]:
        """Index all stored sessions into vector memory.

        Args:
            embed_fn: Function (texts, model) -> list of vectors. If None, uses src.ollama_client.embed.

        Returns:
            List of indexed memory chunks.
        """
        if embed_fn is None:
            embed_fn = self.embed_fn
        if embed_fn is None:
            from src import ollama_client
            def default_embed(texts, model):
                return ollama_client.embed(texts, model=model, host=self.host)
            embed_fn = default_embed

        items_to_embed = []
        texts = []

        for p in sorted(self.sessions_dir.glob("*.json")):
            try:
                session = json.loads(p.read_text())
            except Exception:
                continue

            sid = session.get("id", p.stem)
            stitle = session.get("title", "Untitled")
            turns = session.get("turns", [])

            for idx, turn in enumerate(turns):
                content = turn.get("content", "").strip()
                if not content or len(content) < 3:
                    continue
                role = turn.get("role", "user")
                item_text = f"[{role.upper()}] {content}"
                items_to_embed.append({
                    "id": f"{sid}_t{idx}",
                    "session_id": sid,
                    "session_title": stitle,
                    "role": role,
                    "turn_index": idx,
                    "text": content,
                    "page": 1,  # compatibility with store.py
                })
                texts.append(f"Session '{stitle}': {item_text}")

        if not texts:
            # Empty memory
            store.save([], self.index_path)
            return []

        vectors = embed_fn(texts, self.embed_model)
        for item, vec in zip(items_to_embed, vectors):
            item["vector"] = vec

        store.save(items_to_embed, self.index_path)
        return items_to_embed

    def is_recall_query(self, query: str) -> bool:
        """Determine if a query is asking for recall of past conversation memory."""
        text = (query or "").strip()
        for pat in RECALL_PATTERNS:
            if pat.search(text):
                return True
        return False

    def search_memory(
        self,
        query: str,
        embed_fn: Optional[Callable[[list[str], str], list[list[float]]]] = None,
        top_k: int = 3,
        min_similarity: float = 0.35,
    ) -> list[dict]:
        """Perform semantic search across past sessions.

        Returns top-k matching memory records above min_similarity threshold.
        """
        # Auto-index if index doesn't exist or if sessions are newer than index
        if self.index_path.exists():
            idx_mtime = self.index_path.stat().st_mtime
            if any(p.stat().st_mtime > idx_mtime for p in self.sessions_dir.glob("*.json")):
                try:
                    self.index_sessions(embed_fn=embed_fn)
                except Exception:
                    pass
        else:
            try:
                self.index_sessions(embed_fn=embed_fn)
            except Exception:
                return []

        try:
            records = store.load(self.index_path)
        except Exception:
            return []

        if not records:
            return []

        if embed_fn is None:
            embed_fn = self.embed_fn
        if embed_fn is None:
            from src import ollama_client
            def default_embed(texts, model):
                return ollama_client.embed(texts, model=model, host=self.host)
            embed_fn = default_embed

        query_vec = embed_fn([query], self.embed_model)[0]
        q = np.array(query_vec, dtype=float)
        q_norm = np.linalg.norm(q)
        if q_norm == 0.0:
            return []

        scored = []
        for rec in records:
            v = np.array(rec["vector"], dtype=float)
            if q.shape != v.shape:
                continue
            v_norm = np.linalg.norm(v)
            if v_norm == 0.0:
                continue
            sim = float(np.dot(q, v) / (q_norm * v_norm))
            if sim >= min_similarity:
                scored.append((sim, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, r in scored[:top_k]:
            item = dict(r)
            item["similarity"] = round(sim, 4)
            results.append(item)
        return results

    def format_memory_context(self, memories: list[dict]) -> str:
        """Format retrieved cross-session memories for prompt injection."""
        if not memories:
            return ""
        lines = [
            "### [Cross-Session Recall / External Memory]",
            "The user had prior conversation sessions. Here are the most relevant facts discussed earlier:",
        ]
        for m in memories:
            stitle = m.get("session_title", "Prior Chat")
            role = m.get("role", "user")
            text = m.get("text", "")
            lines.append(f"- (Session '{stitle}', {role}): {text}")
        lines.append("Use these historical facts if they directly answer the user's question.\n")
        return "\n".join(lines)
