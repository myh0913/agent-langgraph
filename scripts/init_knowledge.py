"""
知识库初始化脚本
首次部署时运行此脚本
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge import get_embedder, get_knowledge_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import chromadb
        logger.info("✅ chromadb 已安装")
    except ImportError:
        logger.error("❌ chromadb 未安装，请运行: pip install chromadb")
        return False

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("✅ sentence-transformers 已安装")
    except ImportError:
        logger.error("❌ sentence-transformers 未安装，请运行: pip install sentence-transformers torch")
        return False

    return True


def init_embedder():
    """初始化 Embedder（会下载模型）"""
    logger.info("📦 初始化 Embedder 模型...")
    embedder = get_embedder()
    # 触发模型加载
    _ = embedder.embedding_dim
    logger.info(f"✅ Embedder 就绪: {embedder}")
    return embedder


def check_knowledge_base():
    """检查知识库状态"""
    logger.info("🔍 检查知识库...")
    manager = get_knowledge_manager()
    stats = manager.get_stats()
    logger.info(f"📚 知识库状态: {stats['total_chunks']} chunks")
    return manager


def run():
    """执行初始化"""
    print("=" * 50)
    print("知识库初始化")
    print("=" * 50)

    # 1. 检查依赖
    print("\n[1/3] 检查依赖...")
    if not check_dependencies():
        sys.exit(1)

    # 2. 初始化 Embedder
    print("\n[2/3] 初始化 Embedder 模型...")
    print("   (首次运行会下载模型，约 400MB)")
    init_embedder()

    # 3. 检查知识库
    print("\n[3/3] 检查知识库...")
    check_knowledge_base()

    print("\n" + "=" * 50)
    print("✅ 知识库初始化完成！")
    print("=" * 50)
    print("\n接下来你可以:")
    print("  1. 导入知识: python scripts/import_knowledge.py --file ./knowledge/sources/xxx.md")
    print("  2. 搜索测试: python scripts/test_search.py --query '你的问题'")
    print("  3. 启动 Agent: python main.py")


if __name__ == "__main__":
    run()