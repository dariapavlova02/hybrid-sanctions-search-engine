"""
Char TF-IDF kNN index with optional FAISS HNSW backend.

Falls back to cosine similarity over dense vectors if FAISS is unavailable.
Supports quick ephemeral builds for small candidate pools (e.g., from blocking/AC).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import faiss  # type: ignore

    _FAISS_AVAILABLE = True
except Exception:
    _FAISS_AVAILABLE = False

from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from ....utils.logging_config import get_logger


@dataclass
class VectorIndexConfig:
    ngram_range: Tuple[int, int] = (3, 5)
    min_df: int = 1
    sublinear_tf: bool = True
    norm: str = "l2"
    use_svd: bool = True
    svd_dim: int = 128
    use_faiss: bool = True
    hnsw_m: int = 32
    ef_search: int = 96


class CharTfidfVectorIndex:
    """Builds a char TF-IDF vector index and performs kNN search."""

    def __init__(self, config: Optional[VectorIndexConfig] = None) -> None:
        self.logger = get_logger(__name__)
        self.cfg = config or VectorIndexConfig()
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.svd: Optional[TruncatedSVD] = None
        self.doc_ids: List[str] = []
        self.doc_texts: List[str] = []
        self.X_vec: Optional[np.ndarray] = None  # dense matrix after SVD
        self.faiss_index = None

    def _build_vectorizer(self) -> TfidfVectorizer:
        return TfidfVectorizer(
            analyzer="char",
            ngram_range=self.cfg.ngram_range,
            min_df=self.cfg.min_df,
            sublinear_tf=self.cfg.sublinear_tf,
            norm=self.cfg.norm,
        )

    def _ensure_l2(self, X: np.ndarray) -> np.ndarray:
        try:
            return normalize(X, norm="l2")
        except Exception:
            return X

    def _fit_faiss(self, X: np.ndarray) -> None:
        if not _FAISS_AVAILABLE or not self.cfg.use_faiss:
            return
        dim = X.shape[1]
        # HNSW index over Inner Product (use normalized vectors -> cosine)
        self.faiss_index = faiss.IndexHNSWFlat(dim, self.cfg.hnsw_m)
        try:
            self.faiss_index.hnsw.efSearch = self.cfg.ef_search
        except Exception:
            pass
        self.faiss_index.add(X.astype("float32"))

    def rebuild(self, docs: List[Tuple[str, str]]) -> None:
        """Rebuild index from (doc_id, text) pairs."""
        self.doc_ids = [d[0] for d in docs]
        self.doc_texts = [d[1] for d in docs]
        if not self.doc_texts:
            # Clear state
            self.vectorizer = None
            self.svd = None
            self.X_vec = None
            self.faiss_index = None
            return
        self.vectorizer = self._build_vectorizer()
        X = self.vectorizer.fit_transform(self.doc_texts)

        if self.cfg.use_svd:
            self.svd = TruncatedSVD(
                n_components=min(self.cfg.svd_dim, max(2, X.shape[1] - 1))
            )
            Xr = self.svd.fit_transform(X)
        else:
            # Use dense array cautiously for small doc sets
            Xr = X.toarray() if hasattr(X, "toarray") else np.asarray(X)
        Xr = self._ensure_l2(Xr)
        self.X_vec = Xr.astype("float32")
        self.faiss_index = None
        try:
            self._fit_faiss(self.X_vec)
        except Exception as e:
            self.logger.warning(f"FAISS init failed, fallback to brute-force: {e}")
            self.faiss_index = None

    def _encode(self, text: str) -> Optional[np.ndarray]:
        if not self.vectorizer:
            return None
        Xq = self.vectorizer.transform([text])
        if self.cfg.use_svd and self.svd is not None:
            Xqr = self.svd.transform(Xq)
        else:
            Xqr = Xq.toarray() if hasattr(Xq, "toarray") else np.asarray(Xq)
        Xqr = self._ensure_l2(Xqr)
        return Xqr.astype("float32")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Return list of (doc_id, score) by cosine similarity."""
        if not self.doc_ids or self.X_vec is None:
            return []
        Xq = self._encode(query)
        if Xq is None:
            return []
        q = Xq.astype("float32")
        if self.faiss_index is not None:
            # Use inner product; vectors are L2-normalized -> cosine
            try:
                scores, idx = self.faiss_index.search(q, min(top_k, len(self.doc_ids)))
                ids = [self.doc_ids[i] for i in idx[0] if i >= 0]
                scs = [float(s) for s in scores[0][: len(ids)]]
                return list(zip(ids, scs))
            except Exception as e:
                self.logger.warning(
                    f"FAISS search failed, fallback to brute-force: {e}"
                )
        # Brute-force cosine on dense vectors
        sims = (self.X_vec @ q.T).reshape(-1)
        order = np.argsort(-sims)[:top_k]
        return [(self.doc_ids[i], float(sims[i])) for i in order]
