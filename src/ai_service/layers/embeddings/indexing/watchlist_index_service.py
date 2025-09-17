"""
Watchlist index manager: persistent char TF-IDF kNN index with atomic swap.

Supports active base index + optional delta overlay. Provides load/save snapshot,
atomic reload, and combined search. Stores per-doc metadata and entity_type.
"""

from __future__ import annotations

import json
import os
import pickle
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from ....utils.logging_config import get_logger
from .vector_index_service import CharTfidfVectorIndex, VectorIndexConfig
from .enhanced_vector_index_service import EnhancedVectorIndex, EnhancedVectorIndexConfig


@dataclass
class WatchlistDoc:
    doc_id: str
    text: str
    entity_type: str
    metadata: Dict


class WatchlistIndexService:
    """Manages active + overlay indexes and metadata with atomic swaps."""

    def __init__(self, cfg: Optional[EnhancedVectorIndexConfig] = None) -> None:
        self.logger = get_logger(__name__)
        self.cfg = cfg or EnhancedVectorIndexConfig()
        self._active = EnhancedVectorIndex(self.cfg)
        self._overlay: Optional[EnhancedVectorIndex] = None
        self._docs: Dict[str, WatchlistDoc] = {}
        self._overlay_docs: Dict[str, WatchlistDoc] = {}
        self._active_id: Optional[str] = None
        self._overlay_id: Optional[str] = None

    def ready(self) -> bool:
        return bool(self._active and len(self._docs) > 0)

    def build_from_corpus(
        self, corpus: List[Tuple[str, str, str, Dict]], index_id: Optional[str] = None
    ) -> None:
        """Rebuild active index from corpus of (id, text, entity_type, metadata)."""
        docs = [(doc_id, text) for (doc_id, text, _et, _md) in corpus]
        self._active.rebuild(docs)
        self._docs = {
            doc_id: WatchlistDoc(doc_id, text, et, md)
            for (doc_id, text, et, md) in corpus
        }
        self._active_id = index_id or "in-memory"
        self.logger.info(
            f"Watchlist active index built: {len(self._docs)} docs, id={self._active_id}"
        )

    def set_overlay_from_corpus(
        self, corpus: List[Tuple[str, str, str, Dict]], overlay_id: Optional[str] = None
    ) -> None:
        idx = EnhancedVectorIndex(self.cfg)
        docs = [(doc_id, text) for (doc_id, text, _et, _md) in corpus]
        idx.rebuild(docs)
        self._overlay = idx
        self._overlay_docs = {
            doc_id: WatchlistDoc(doc_id, text, et, md)
            for (doc_id, text, et, md) in corpus
        }
        self._overlay_id = overlay_id or "overlay"
        self.logger.info(
            f"Watchlist overlay set: {len(self._overlay_docs)} docs, id={self._overlay_id}"
        )

    def clear_overlay(self) -> None:
        self._overlay = None
        self._overlay_docs = {}
        self._overlay_id = None

    def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """Search overlay then active; merge unique doc_ids preserving best score."""
        results: Dict[str, float] = {}
        # Overlay first
        if self._overlay is not None:
            for doc_id, s in self._overlay.search(query, top_k=min(top_k, 200)):
                results[doc_id] = max(results.get(doc_id, 0.0), float(s))
        # Active
        for doc_id, s in self._active.search(query, top_k=min(top_k, 200)):
            results[doc_id] = max(results.get(doc_id, 0.0), float(s))
        # Top-k by score
        items = sorted(results.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return items

    def get_doc(self, doc_id: str) -> Optional[WatchlistDoc]:
        return self._overlay_docs.get(doc_id) or self._docs.get(doc_id)

    # ---- Snapshot I/O ---------------------------------------------------

    def save_snapshot(self, snapshot_dir: str, as_overlay: bool = False) -> Dict:
        os.makedirs(snapshot_dir, exist_ok=True)
        idx = self._overlay if as_overlay else self._active
        if idx is None:
            raise RuntimeError("No index to save")
        # Persist vectorizer + svd + doc ids/texts + dense vectors
        with open(os.path.join(snapshot_dir, "vectorizer.pkl"), "wb") as f:
            pickle.dump(idx.vectorizer, f)
        with open(os.path.join(snapshot_dir, "svd.pkl"), "wb") as f:
            pickle.dump(idx.svd, f)
        data = {
            "doc_ids": idx.doc_ids,
            "doc_texts": idx.doc_texts,
            "index_config": self.cfg.__dict__,
        }
        with open(os.path.join(snapshot_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
        if idx.X_vec is not None:
            np.save(os.path.join(snapshot_dir, "X_vec.npy"), idx.X_vec)
        # Save FAISS if present
        try:
            import faiss  # type: ignore

            if idx.faiss_index is not None:
                faiss.write_index(
                    idx.faiss_index, os.path.join(snapshot_dir, "faiss.index")
                )
        except Exception:
            pass
        # Save doc metadata
        dmap = self._overlay_docs if as_overlay else self._docs
        md = {
            k: {"text": v.text, "entity_type": v.entity_type, "metadata": v.metadata}
            for k, v in dmap.items()
        }
        with open(os.path.join(snapshot_dir, "docs.json"), "w", encoding="utf-8") as f:
            json.dump(md, f, ensure_ascii=False)
        return {"saved": True, "path": snapshot_dir}

    def _load_char_index(self, snapshot_dir: str) -> CharTfidfVectorIndex:
        # Load vectorizer + svd + docs + vectors + faiss (if available)
        with open(os.path.join(snapshot_dir, "meta.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)
        cfg = VectorIndexConfig(**meta.get("index_config", {}))
        idx = CharTfidfVectorIndex(cfg)
        with open(os.path.join(snapshot_dir, "vectorizer.pkl"), "rb") as f:
            idx.vectorizer = pickle.load(f)
        with open(os.path.join(snapshot_dir, "svd.pkl"), "rb") as f:
            idx.svd = pickle.load(f)
        idx.doc_ids = meta.get("doc_ids", [])
        idx.doc_texts = meta.get("doc_texts", [])
        xvec_path = os.path.join(snapshot_dir, "X_vec.npy")
        if os.path.exists(xvec_path):
            try:
                idx.X_vec = np.load(xvec_path).astype("float32")
            except Exception:
                idx.X_vec = None
        # Load faiss index if present
        try:
            import faiss  # type: ignore

            fpath = os.path.join(snapshot_dir, "faiss.index")
            if os.path.exists(fpath):
                idx.faiss_index = faiss.read_index(fpath)
        except Exception:
            idx.faiss_index = None
        return idx

    def reload_snapshot(self, snapshot_dir: str, as_overlay: bool = False) -> Dict:
        idx = self._load_char_index(snapshot_dir)
        # Load docs metadata
        docs_path = os.path.join(snapshot_dir, "docs.json")
        with open(docs_path, "r", encoding="utf-8") as f:
            md = json.load(f)
        if as_overlay:
            self._overlay = idx
            self._overlay_docs = {
                k: WatchlistDoc(
                    k, v["text"], v.get("entity_type", ""), v.get("metadata", {})
                )
                for k, v in md.items()
            }
            self._overlay_id = snapshot_dir
            info = {
                "overlay_loaded": True,
                "overlay_count": len(self._overlay_docs),
                "path": snapshot_dir,
            }
        else:
            self._active = idx
            self._docs = {
                k: WatchlistDoc(
                    k, v["text"], v.get("entity_type", ""), v.get("metadata", {})
                )
                for k, v in md.items()
            }
            self._active_id = snapshot_dir
            info = {
                "active_loaded": True,
                "active_count": len(self._docs),
                "path": snapshot_dir,
            }
        self.logger.info(f"Watchlist snapshot loaded: {info}")
        return info

    def status(self) -> Dict:
        return {
            "active": {"id": self._active_id, "count": len(self._docs)},
            "overlay": {"id": self._overlay_id, "count": len(self._overlay_docs)},
        }
