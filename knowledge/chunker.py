"""
文本分块模块
"""
import re
from typing import List, Dict, Any
from pathlib import Path
import json


class TextChunker:
    """文本分块器"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_length: int = 50
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length

    def chunk_text(self, text: str, source: str = "", metadata: Dict = None) -> List[Dict[str, Any]]:
        """将文本分块"""
        if not text or len(text.strip()) < self.min_chunk_length:
            return []

        metadata = metadata or {}

        # 按段落分割
        paragraphs = self._split_paragraphs(text)

        # 合并段落为块
        chunks = self._merge_to_chunks(paragraphs)

        result = []
        for i, chunk_content in enumerate(chunks):
            if len(chunk_content.strip()) < self.min_chunk_length:
                continue

            chunk_id = self._generate_chunk_id(source, i)

            result.append({
                "id": chunk_id,
                "content": chunk_content.strip(),
                "source": source,
                "title": self._extract_title(chunk_content),
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "char_count": len(chunk_content)
                }
            })

        return result

    def _split_paragraphs(self, text: str) -> List[str]:
        lines = text.split("\n")
        paragraphs = []
        current = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current:
                    paragraphs.append("\n".join(current))
                    current = []
                continue
            if stripped.startswith("#"):
                if current:
                    paragraphs.append("\n".join(current))
                    current = []
                continue
            current.append(stripped)

        if current:
            paragraphs.append("\n".join(current))

        return [p for p in paragraphs if p.strip()]

    def _merge_to_chunks(self, paragraphs: List[str]) -> List[str]:
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            if para_size > self.chunk_size:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0

                sub_chunks = self._split_long_paragraph(para)
                chunks.extend(sub_chunks)
                continue

            if current_size + para_size > self.chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                overlap_text = "\n".join(current_chunk)[-self.chunk_overlap:]
                current_chunk = [overlap_text] if overlap_text.strip() else []
                current_size = len(overlap_text)

            current_chunk.append(para)
            current_size += para_size + 1

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def _split_long_paragraph(self, text: str) -> List[str]:
        sentences = re.split(r"([。！？；\n])", text)
        chunks = []
        current = []
        current_size = 0

        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            separator = sentences[i + 1] if i + 1 < len(sentences) else ""
            full_sentence = sentence + separator
            sent_size = len(full_sentence)

            if current_size + sent_size > self.chunk_size and current:
                chunks.append("".join(current))
                current = [sentence]
                current_size = len(sentence)
                if separator:
                    current.append(separator)
                    current_size += len(separator)
            else:
                current.append(full_sentence)
                current_size += sent_size

        if current:
            chunks.append("".join(current))

        return chunks

    def _generate_chunk_id(self, source: str, index: int) -> str:
        import hashlib
        import time

        prefix = Path(source).stem if source else "doc"
        timestamp = int(time.time() * 1000)
        raw = f"{prefix}_{timestamp}_{index}"
        hash_str = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"chunk_{prefix}_{hash_str}"

    def _extract_title(self, content: str) -> str:
        first_line = content.split("\n")[0].strip()
        if first_line.startswith("#"):
            first_line = first_line.lstrip("#").strip()
        return first_line[:100] if first_line else "无标题"

    def chunk_file(self, file_path: str, encoding: str = "utf-8") -> List[Dict[str, Any]]:
        """从文件分块"""
        path = Path(file_path)
        text = path.read_text(encoding=encoding, errors="ignore")

        metadata = {
            "file_name": path.name,
            "file_ext": path.suffix,
            "file_size": path.stat().st_size
        }

        return self.chunk_text(text, source=str(path), metadata=metadata)