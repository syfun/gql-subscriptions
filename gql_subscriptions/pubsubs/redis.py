import asyncio
import json
from typing import Any, Callable, Optional, Dict, Tuple

import aioredis
from gql_subscriptions.engine import PubSubEngine


class RedisPubSub(PubSubEngine):
    """Dumps publish payload, if none, use json.dumps"""
    dumps: Callable
    subscriptions: Dict[int, Tuple[str, aioredis.Channel, asyncio.Task]]
    current_sub_id: int = 0
    redis: Optional[aioredis.Redis] = None

    def __init__(self, address: str, dumps: Callable = None) -> None:
        self.address = address
        self.dumps = dumps or json.dumps
        self.subscriptions = {}

    async def connect(self) -> None:
        self.redis = await aioredis.create_redis_pool(self.address)

    async def disconnect(self) -> None:
        self.redis.close()
        await self.redis.wait_closed()

    async def publish(self, trigger: str, payload: Any) -> None:
        if not self.redis:
            await self.connect()
        await self.redis.publish(trigger, self.dumps(payload))

    async def subscribe(self, trigger_name: str, on_message: Callable, options: dict = None) -> int:
        async def reader(ch: aioredis.Channel):
            while await ch.wait_message():
                msg = await ch.get_json()
                result = on_message(msg)
                if asyncio.iscoroutine(result):
                    await result

        if not self.redis:
            await self.connect()
        (channel,) = await self.redis.subscribe(trigger_name)
        self.current_sub_id += 1
        self.subscriptions[self.current_sub_id] = (
            trigger_name,
            channel,
            asyncio.create_task(reader(channel)),
        )
        return self.current_sub_id

    async def unsubscribe(self, sub_id: int) -> None:
        if sub_id not in self.subscriptions:
            return

        trigger_name, channel, task = self.subscriptions.pop(sub_id)
        channel.close()
        task.cancel()
