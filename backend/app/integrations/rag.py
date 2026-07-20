"""Local LlamaIndex retrieval for the optional student recommendation mode.

The RAG path is deliberately optional.  Importing this module does not import
LlamaIndex or a model, so the existing rule/DeepSeek path remains usable in a
minimal development environment.  When enabled, course summaries are
embedded with the repository-local HuggingFace model and persisted under the
project ``storage`` directory.  A catalog fingerprint gives each catalog
snapshot its own small persisted index and avoids serving stale course data.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RAGUnavailable(RuntimeError):
    """Raised when the optional local RAG pipeline cannot be used."""


@dataclass(frozen=True)
class RAGResult:
    course_ids: list[str]
    context: str


def _project_root() -> Path:
    # backend/app/integrations/rag.py -> project root
    return Path(__file__).resolve().parents[3]


def _default_embedding_model() -> str:
    return "BAAI/bge-small-zh-v1.5"


def _default_storage_path() -> Path:
    return _project_root() / "storage" / "rag"


def _resolve_hf_home_model(model_name: str) -> str | None:
    """检查模型是否已存在于 HF_HOME 缓存中，返回模型名称或 None。

    HuggingFace 缓存结构：
    - HF_HOME/hub/models--{org}--{model}/  (HF_HOME 指向基础目录)
    - HUGGINGFACE_HUB_CACHE/models--{org}--{model}/  (直接指向 hub 目录)
    - ~/.cache/huggingface/hub/models--{org}--{model}/  (默认路径)
    """
    hf_home = os.getenv("HF_HOME")
    hf_cache = os.getenv("HUGGINGFACE_HUB_CACHE")

    # 构建可能的缓存路径列表
    cache_dir_name = "models--" + model_name.replace("/", "--")
    possible_paths = []

    if hf_cache:
        possible_paths.append(Path(hf_cache) / cache_dir_name)
    if hf_home:
        possible_paths.append(Path(hf_home) / "hub" / cache_dir_name)
        possible_paths.append(Path(hf_home) / cache_dir_name)

    # 默认路径
    default_hub = Path.home() / ".cache" / "huggingface" / "hub"
    possible_paths.append(default_hub / cache_dir_name)

    for cache_path in possible_paths:
        if cache_path.is_dir():
            return model_name
    return None


def _get_hf_cache_dir() -> str | None:
    """获取 HuggingFace 缓存目录路径，用于离线加载模型。"""
    hf_home = os.getenv("HF_HOME")
    hf_cache = os.getenv("HUGGINGFACE_HUB_CACHE")

    if hf_cache and Path(hf_cache).is_dir():
        return hf_cache
    if hf_home:
        hub_path = Path(hf_home) / "hub"
        if hub_path.is_dir():
            return str(hub_path)
        if Path(hf_home).is_dir():
            return hf_home

    default_hub = Path.home() / ".cache" / "huggingface" / "hub"
    if default_hub.is_dir():
        return str(default_hub)
    return None


def _as_int(value: str, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _schedule_text(schedule: dict[str, Any]) -> str:
    weekday = schedule.get("weekday", "?")
    start = schedule.get("start_minute", "?")
    end = schedule.get("end_minute", "?")
    room = schedule.get("room", "TBD")
    return f"weekday={weekday}, start={start}, end={end}, room={room}"


def _course_text(course: dict[str, Any]) -> str:
    schedules = "; ".join(_schedule_text(item) for item in course.get("schedules", [])) or "none"
    prerequisites = ", ".join(str(item) for item in course.get("prerequisites", [])) or "none"
    return (
        f"course_id={course.get('id', '')}\n"
        f"code={course.get('code', '')}\n"
        f"name={course.get('name', '')}\n"
        f"teacher={course.get('teacher_name', '')}\n"
        f"credits={course.get('credits', '')}\n"
        f"capacity={course.get('capacity', '')}\n"
        f"schedules={schedules}\n"
        f"prerequisites={prerequisites}"
    )


class LocalCourseRAG:
    """Build/load a local LlamaIndex vector index over the live course list."""

    def __init__(
        self,
        *,
        embedding_model: str | None = None,
        storage_path: str | Path | None = None,
        top_k: int | None = None,
    ) -> None:
        self.embedding_model = (
            embedding_model
            or os.getenv("RAG_EMBEDDING_MODEL", _default_embedding_model())
        )
        self.storage_path = Path(
            storage_path or os.getenv("RAG_STORAGE_PATH", str(_default_storage_path()))
        ).expanduser()
        self.top_k = top_k or _as_int(os.getenv("RAG_TOP_K", "8"), 8)
        self.device = os.getenv("RAG_DEVICE", "cpu").strip() or "cpu"
        self._index: Any | None = None
        self._catalog_fingerprint: str | None = None
        self._embed_model: Any | None = None
        self._lock = threading.RLock()

    @staticmethod
    def _fingerprint(catalog: list[dict[str, Any]]) -> str:
        normalized = [
            {
                "id": course.get("id"),
                "code": course.get("code"),
                "name": course.get("name"),
                "teacher_name": course.get("teacher_name", ""),
                "credits": course.get("credits"),
                "capacity": course.get("capacity"),
                "status": course.get("status"),
                "schedules": course.get("schedules", []),
                "prerequisites": course.get("prerequisites", []),
            }
            for course in catalog
        ]
        raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:24]

    def _load_dependencies(self):
        try:
            from llama_index.core import Document, StorageContext, VectorStoreIndex, load_index_from_storage
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        except ImportError as exc:
            raise RAGUnavailable("RAG_DEPENDENCY_MISSING") from exc
        return Document, StorageContext, VectorStoreIndex, load_index_from_storage, HuggingFaceEmbedding

    def _embed(self, embedding_type: Any) -> Any:
        if self._embed_model is None:
            # 检查模型是否已在 HF_HOME 缓存中
            local_model = _resolve_hf_home_model(self.embedding_model)
            cache_dir = _get_hf_cache_dir()

            try:
                # 优先使用离线模式（本地缓存）
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                os.environ["HF_HUB_OFFLINE"] = "1"

                # 如果有本地缓存，传入 cache_dir 参数
                embed_kwargs = {
                    "model_name": self.embedding_model,
                    "device": self.device,
                    "normalize": True,
                }
                if cache_dir:
                    embed_kwargs["cache_folder"] = cache_dir

                self._embed_model = embedding_type(**embed_kwargs)
            except Exception:
                # 离线失败，尝试在线模式（仅当本地无缓存时）
                if local_model:
                    # 本地有缓存但加载失败，直接报错
                    raise RAGUnavailable("RAG_EMBEDDING_LOAD_FAILED")
                try:
                    os.environ.pop("TRANSFORMERS_OFFLINE", None)
                    os.environ.pop("HF_HUB_OFFLINE", None)
                    self._embed_model = embedding_type(
                        model_name=self.embedding_model,
                        device=self.device,
                        normalize=True,
                    )
                except Exception as exc:
                    raise RAGUnavailable("RAG_EMBEDDING_LOAD_FAILED") from exc
        return self._embed_model

    def _build_or_load(self, catalog: list[dict[str, Any]]) -> Any:
        Document, StorageContext, VectorStoreIndex, load_index_from_storage, embedding_type = self._load_dependencies()

        fingerprint = self._fingerprint(catalog)
        if self._index is not None and self._catalog_fingerprint == fingerprint:
            return self._index

        self.storage_path.mkdir(parents=True, exist_ok=True)
        index_path = self.storage_path / fingerprint
        embed_model = self._embed(embedding_type)

        if index_path.is_dir() and any(index_path.iterdir()):
            try:
                storage_context = StorageContext.from_defaults(persist_dir=str(index_path))
                self._index = load_index_from_storage(storage_context, embed_model=embed_model)
                self._catalog_fingerprint = fingerprint
                return self._index
            except Exception:
                # A partial/corrupt persisted index is rebuilt from the live
                # catalog.  Do not make the student recommendation endpoint
                # depend on an old local cache.
                self._index = None

        documents = [
            Document(text=_course_text(course), metadata={"course_id": str(course["id"])})
            for course in catalog
            if course.get("id")
        ]
        if not documents:
            raise RAGUnavailable("RAG_CATALOG_EMPTY")
        try:
            index = VectorStoreIndex.from_documents(
                documents,
                embed_model=embed_model,
                show_progress=False,
            )
            index.storage_context.persist(persist_dir=str(index_path))
        except Exception as exc:
            raise RAGUnavailable("RAG_INDEX_BUILD_FAILED") from exc
        self._index = index
        self._catalog_fingerprint = fingerprint
        return index

    def _retrieve_sync(self, query: str, catalog: list[dict[str, Any]]) -> RAGResult:
        if not catalog:
            raise RAGUnavailable("RAG_CATALOG_EMPTY")
        with self._lock:
            index = self._build_or_load(catalog)
            try:
                retriever = index.as_retriever(similarity_top_k=min(self.top_k, len(catalog)))
                nodes = retriever.retrieve(query)
            except Exception as exc:
                raise RAGUnavailable("RAG_RETRIEVE_FAILED") from exc

        course_ids: list[str] = []
        context_lines: list[str] = []
        for item in nodes:
            node = getattr(item, "node", item)
            metadata = getattr(node, "metadata", {}) or {}
            course_id = metadata.get("course_id")
            if not course_id or course_id in course_ids:
                continue
            course_ids.append(str(course_id))
            score = getattr(item, "score", None)
            score_text = f" score={score:.4f}" if isinstance(score, (int, float)) else ""
            context_lines.append(f"{_course_text(next(course for course in catalog if str(course.get('id')) == str(course_id)))}{score_text}")

        if not course_ids:
            raise RAGUnavailable("RAG_NO_MATCH")
        return RAGResult(course_ids=course_ids, context="\n\n---\n\n".join(context_lines))

    async def retrieve(self, payload: Any, snapshot: dict[str, Any]) -> RAGResult:
        preferences = ", ".join(str(item) for item in getattr(payload, "preferences", []) or []) or "none"
        selected = ", ".join(
            f"{course.get('code', course.get('id', ''))} {course.get('name', '')}"
            for course in snapshot.get("selected_courses", [])
        ) or "none"
        query = (
            f"learning goals: {getattr(payload, 'goals', '')}\n"
            f"preferences: {preferences}\n"
            f"already selected courses and timetable: {selected}\n"
            "find the most relevant open courses without making the final eligibility decision"
        )
        return await asyncio.to_thread(self._retrieve_sync, query, list(snapshot.get("catalog", [])))


DEFAULT_RAG = LocalCourseRAG()
