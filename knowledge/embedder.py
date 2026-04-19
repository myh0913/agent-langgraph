"""
本地 Embedding 模型
使用 sentence-transformers 加载 all-MiniLM-L6-v2
"""
from typing import List

from .config import knowledge_settings


class LocalEmbedder:
    """
    本地 Embedding 模型封装
    使用 all-MiniLM-L6-v2 生成文本向量
    """

    _instance = None
    _model = None
    _loaded = False  # 模块级标记，避免重复打印

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = None, device: str = None):
        if getattr(self, "_initialized", False):
            return

        self.model_name = model_name or knowledge_settings.EMBEDDING_MODEL_NAME
        self.device = device or knowledge_settings.EMBEDDING_DEVICE
        self.embedding_dim = knowledge_settings.EMBEDDING_DIM
        self._model = None
        self._initialized = True

    @property
    def model(self):
        if self._model is None:
            LocalEmbedder._loaded = True  # 标记已触发过加载
            self._load_model()
        return self._model

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer

            local_model_path = knowledge_settings.MODELS_DIR / self.model_name
            if local_model_path.exists():
                if not LocalEmbedder._loaded:
                    print(f"📦 从本地加载模型: {local_model_path}")
                self._model = SentenceTransformer(
                    str(local_model_path),
                    device=self.device
                )
            else:
                if not LocalEmbedder._loaded:
                    print(f"⬇️  首次使用将自动下载模型到: {knowledge_settings.MODELS_DIR}")
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    cache_folder=str(knowledge_settings.MODELS_DIR)
                )

            if not LocalEmbedder._loaded:
                print(f"✅ 模型加载成功: {self.model_name}")
                print(f"   设备: {self.device}")
                print(f"   向量维度: {self.embedding_dim}")
                LocalEmbedder._loaded = True

        except ImportError:
            raise ImportError(
                "sentence-transformers 未安装。\n"
                "请运行: pip install sentence-transformers torch"
            )

    def embed(self, text: str) -> List[float]:
        """生成单条文本的向量"""
        if not text or not text.strip():
            return [0.0] * self.embedding_dim

        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量生成向量"""
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100
        )
        return embeddings.tolist()

    def __repr__(self):
        return f"LocalEmbedder(model={self.model_name}, device={self.device}, dim={self.embedding_dim})"


_embedder = None


def get_embedder() -> LocalEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = LocalEmbedder()
    return _embedder