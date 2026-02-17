"""Redis 기반 LangGraph 체크포인트 저장소.

대화별(thread_id = conversation_id) 에이전트 상태를 Redis에 저장하고
복원하여 대화 컨텍스트를 유지합니다.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RedisCheckpointStore:
    """Redis 기반 체크포인트 저장소.

    각 대화(thread_id)의 에이전트 그래프 상태를 저장/복원합니다.
    - 키 형식: checkpoint:{thread_id}
    - TTL: 7일 (대화 비활성 시 자동 만료)
    """

    PREFIX = "checkpoint"
    TTL_SECONDS = 7 * 24 * 3600  # 7일

    def __init__(self, redis_client):
        self.redis = redis_client

    def _key(self, thread_id: str) -> str:
        return f"{self.PREFIX}:{thread_id}"

    async def save(self, thread_id: str, state: dict) -> None:
        """그래프 상태를 Redis에 저장"""
        try:
            checkpoint = {
                "state": state,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self.redis.set(
                self._key(thread_id),
                json.dumps(checkpoint, ensure_ascii=False, default=str),
                ex=self.TTL_SECONDS,
            )
        except Exception as e:
            logger.warning(f"Checkpoint save failed for {thread_id}: {e}")

    async def load(self, thread_id: str) -> dict | None:
        """저장된 그래프 상태 복원"""
        try:
            data = await self.redis.get(self._key(thread_id))
            if data:
                checkpoint = json.loads(data)
                return checkpoint.get("state")
        except Exception as e:
            logger.warning(f"Checkpoint load failed for {thread_id}: {e}")
        return None

    async def delete(self, thread_id: str) -> None:
        """체크포인트 삭제"""
        try:
            await self.redis.delete(self._key(thread_id))
        except Exception as e:
            logger.warning(f"Checkpoint delete failed for {thread_id}: {e}")

    async def exists(self, thread_id: str) -> bool:
        """체크포인트 존재 여부"""
        try:
            return bool(await self.redis.exists(self._key(thread_id)))
        except Exception:
            return False
