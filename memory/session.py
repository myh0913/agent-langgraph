"""
会话管理模块
基于 Redis 实现，支持多节点部署
"""
import json
import redis
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from config.settings import settings


class SessionManager:
    """
    会话管理器（Redis 版）
    支持多用户会话隔离、会话历史存储和查询
    """

    # Redis Key 前缀
    _USER_KEY = "agent:user:{user_id}"
    _SESSION_KEY = "agent:session:{session_id}"
    _SESSION_LIST_KEY = "agent:user_sessions:{user_id}"
    _MSG_LIST_KEY = "agent:messages:{session_id}"
    _SESSION_TTL = 60 * 60 * 24 * 30  # 30 天过期

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化会话管理器

        Args:
            redis_url: Redis 连接 URL，默认使用配置中的
        """
        self.redis_url = redis_url or getattr(settings, 'REDIS_URL', None)
        self._client: Optional[redis.Redis] = None
        self._lock = threading.Lock()

    @property
    def client(self) -> redis.Redis:
        """懒加载 Redis 客户端"""
        if self._client is None:
            self._client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._client

    def _ensure_connection(self):
        """测试连接"""
        self.client.ping()

    def get_or_create_user(self, user_id: str) -> bool:
        """
        获取或创建用户

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否是新创建的用户
        """
        key = self._USER_KEY.format(user_id=user_id)
        is_new = not self.client.exists(key)
        self.client.hset(key, mapping={
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        })
        self.client.expire(key, self._SESSION_TTL)
        return is_new

    def get_or_create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        获取或创建会话

        Args:
            user_id: 用户ID
            session_id: 可选的会话ID，如果为 None 则创建新会话

        Returns:
            str: 会话ID
        """
        self.get_or_create_user(user_id)

        if session_id:
            # 验证会话是否存在
            session_key = self._SESSION_KEY.format(session_id=session_id)
            if self.client.exists(session_key):
                self.client.hset(session_key, "last_active", datetime.now().isoformat())
                self.client.expire(session_key, self._SESSION_TTL)
                return session_id

        # 创建新会话
        import uuid
        new_session_id = session_id or str(uuid.uuid4())
        session_key = self._SESSION_KEY.format(session_id=new_session_id)
        now = datetime.now().isoformat()
        self.client.hset(session_key, mapping={
            "user_id": user_id,
            "created_at": now,
            "last_active": now
        })
        self.client.expire(session_key, self._SESSION_TTL)

        # 加入用户的会话列表（score 用时间戳）
        list_key = self._SESSION_LIST_KEY.format(user_id=user_id)
        self.client.zadd(list_key, {new_session_id: datetime.now().timestamp()})

        return new_session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        添加消息到会话

        Args:
            session_id: 会话ID
            role: 角色 ('user' 或 'assistant')
            content: 消息内容
            metadata: 额外的元数据
        """
        session_key = self._SESSION_KEY.format(session_id=session_id)
        if not self.client.exists(session_key):
            return

        msg = {
            "role": role,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps(metadata) if metadata else None
        }

        # 消息写入列表
        msg_key = self._MSG_LIST_KEY.format(session_id=session_id)
        self.client.rpush(msg_key, json.dumps(msg, ensure_ascii=False))
        self.client.expire(msg_key, self._SESSION_TTL)

        # 更新会话活跃时间
        self.client.hset(session_key, "last_active", datetime.now().isoformat())
        self.client.expire(session_key, self._SESSION_TTL)

        # 更新会话在列表中的排序分值
        user_id = self.client.hget(session_key, "user_id")
        if user_id:
            list_key = self._SESSION_LIST_KEY.format(user_id=user_id)
            self.client.zadd(list_key, {session_id: datetime.now().timestamp()})

    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取会话历史

        Args:
            session_id: 会话ID
            limit: 限制返回的消息数量

        Returns:
            List[Dict]: 消息列表
        """
        msg_key = self._MSG_LIST_KEY.format(session_id=session_id)
        if not self.client.exists(msg_key):
            return []

        if limit:
            raw = self.client.lrange(msg_key, -limit, -1)
        else:
            raw = self.client.lrange(msg_key, 0, -1)

        messages = []
        for item in raw:
            try:
                msg = json.loads(item)
                messages.append(msg)
            except json.JSONDecodeError:
                continue

        if limit:
            messages.reverse()

        return messages

    def get_user_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取用户的所有会话

        Args:
            user_id: 用户ID
            limit: 限制返回数量

        Returns:
            List[Dict]: 会话列表
        """
        list_key = self._SESSION_LIST_KEY.format(user_id=user_id)

        # 按活跃时间倒序取最新的 limit 个
        session_ids = self.client.zrevrange(list_key, 0, limit - 1)
        if not session_ids:
            return []

        sessions = []
        for sid in session_ids:
            session_key = self._SESSION_KEY.format(session_id=sid)
            data = self.client.hgetall(session_key)
            if data:
                sessions.append({
                    "session_id": sid,
                    "created_at": data.get("created_at", ""),
                    "last_active": data.get("last_active", "")
                })

        return sessions

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """
        删除会话及其所有消息

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            bool: 是否成功删除
        """
        session_key = self._SESSION_KEY.format(session_id=session_id)

        # 验证会话所属用户
        data = self.client.hgetall(session_key)
        if not data or data.get("user_id") != user_id:
            return False

        # 删除消息列表
        msg_key = self._MSG_LIST_KEY.format(session_id=session_id)
        self.client.delete(msg_key)

        # 删除会话
        self.client.delete(session_key)

        # 从用户会话列表移除
        list_key = self._SESSION_LIST_KEY.format(user_id=user_id)
        self.client.zrem(list_key, session_id)

        return True

    def cleanup_expired_sessions(self, hours: Optional[int] = None):
        """
        清理过期的会话（Redis 自动过期，此方法留空）

        Args:
            hours: 过期小时数（Redis TTL 自动处理）
        """
        # Redis key 已设置过期时间，此方法无需实现
        pass
