"""
测试知识库检索
"""
import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge import get_knowledge_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="测试知识库检索")
    parser.add_argument("--query", "-q", required=True, help="查询内容")
    parser.add_argument("--top", "-k", type=int, default=5, help="返回条数")
    parser.add_argument("--category", "-c", help="按分类过滤")
    parser.add_argument("--tags", nargs="+", help="按标签过滤")

    args = parser.parse_args()

    manager = get_knowledge_manager()

    # 打印知识库状态
    stats = manager.get_stats()
    logger.info(f"知识库状态: {stats['total_chunks']} chunks")

    # 执行检索
    results = manager.search(
        query=args.query,
        top_k=args.top,
        category=args.category,
        tags=args.tags
    )

    if not results:
        logger.info("没有找到相关结果")
        return

    print(f"\n{'=' * 60}")
    print(f"查询: {args.query}")
    print(f"结果: {len(results)} 条")
    print(f"{'=' * 60}\n")

    for i, r in enumerate(results, 1):
        print(f"[{i}] Score: {r['score']:.4f} | Category: {r['category']}")
        print(f"    Title: {r['title']}")
        print(f"    Tags: {', '.join(r.get('tags', []))}")
        print(f"    Content: {r['content'][:200]}...")
        print(f"    Source: {r['source']}")
        print()


if __name__ == "__main__":
    main()