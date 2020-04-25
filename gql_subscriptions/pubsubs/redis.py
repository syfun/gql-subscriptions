import asyncio
import json
from typing import Any, Callable, Dict, Optional, Tuple

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
        self.triggers = {}

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
        if not self.redis:
            await self.connect()

        async def reader(ch: aioredis.Channel, trigger_name: str):
            while await ch.wait_message():
                msg = await ch.get_json()
                *_, handlers = self.triggers.get(trigger_name)
                await asyncio.gather(*[handler(msg) for handler in handlers.values()])

        self.current_sub_id += 1
        self.subscriptions[self.current_sub_id] = trigger_name
        if trigger_name not in self.triggers:
            (channel,) = await self.redis.subscribe(trigger_name)
            self.triggers[trigger_name] = (
                channel,
                asyncio.create_task(reader(channel, trigger_name)),
                {self.current_sub_id: on_message},
            )
        else:
            *_, handlers = self.triggers[trigger_name]
            handlers[self.current_sub_id] = on_message
        return self.current_sub_id

    async def unsubscribe(self, sub_id: int) -> None:
        if sub_id not in self.subscriptions:
            return

        trigger_name = self.subscriptions.pop(sub_id)
        channel, task, handlers = self.triggers[trigger_name]
        handlers.pop(sub_id, None)
        if not handlers:
            channel.close()
            task.cancel()
