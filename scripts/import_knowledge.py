"""
导入知识文件到知识库
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
    parser = argparse.ArgumentParser(description="导入知识文件到向量数据库")
    parser.add_argument("--file", "-f", help="单个文件路径")
    parser.add_argument("--dir", "-d", help="目录路径（批量导入）")
    parser.add_argument("--text", "-t", help="直接传入文本内容")
    parser.add_argument("--category", "-c", default="通用", help="知识分类")
    parser.add_argument("--tags", nargs="+", default=[], help="知识标签")
    parser.add_argument("--title", help="文本标题（用于 --text 模式）")
    parser.add_argument("--recursive", "-r", action="store_true", help="递归子目录")

    args = parser.parse_args()

    manager = get_knowledge_manager()

    if args.file:
        result = manager.import_file(
            file_path=args.file,
            category=args.category,
            tags=args.tags
        )
        if result["success"]:
            logger.info(f"✅ 导入成功: {result['total_chunks']} 个 chunks")
        else:
            logger.error(f"❌ 导入失败: {result.get('error')}")

    elif args.dir:
        result = manager.import_directory(
            dir_path=args.dir,
            category=args.category,
            tags=args.tags,
            recursive=args.recursive
        )
        logger.info(f"✅ 批量导入完成: {result['total_files']} 个文件, {result['total_chunks']} 个 chunks")
        if result.get("failed_count", 0) > 0:
            logger.warning(f"⚠️ {result['failed_count']} 个文件导入失败")

    elif args.text:
        result = manager.import_text(
            text=args.text,
            title=args.title or "手动导入",
            category=args.category,
            tags=args.tags
        )
        if result["success"]:
            logger.info(f"✅ 文本导入成功: {result['total_chunks']} 个 chunks")
        else:
            logger.error(f"❌ 导入失败: {result.get('error')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()