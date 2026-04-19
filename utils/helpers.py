"""
通用辅助函数
"""
import re
import hashlib
from typing import Any, Dict
from datetime import datetime

def generate_hash(text: str) -> str:
    """
    生成文本的 MD5 哈希
    
    Args:
        text: 输入文本
        
    Returns:
        str: MD5 哈希值
    """
    return hashlib.md5(text.encode()).hexdigest()

def format_timestamp(dt: datetime = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳
    
    Args:
        dt: datetime 对象，默认当前时间
        fmt: 格式化字符串
        
    Returns:
        str: 格式化后的时间字符串
    """
    dt = dt or datetime.now()
    return dt.strftime(fmt)

def safe_get(dictionary: Dict, *keys, default: Any = None) -> Any:
    """
    安全获取嵌套字典的值
    
    Args:
        dictionary: 字典对象
        *keys: 嵌套的键路径
        default: 默认值
        
    Returns:
        Any: 获取到的值或默认值
    """
    result = dictionary
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result if result is not None else default

def clean_text(text: str) -> str:
    """
    清理文本，移除多余空白字符
    
    Args:
        text: 输入文本
        
    Returns:
        str: 清理后的文本
    """
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 输入文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
