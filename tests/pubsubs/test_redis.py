import asyncio

import pytest

from gql_subscriptions.pubsubs.redis import RedisPubSub


@pytest.fixture()
def pubsub(scope='function'):
    return RedisPubSub('redis://localhost:6379')


def on_message1(message):
    print(f'on message1: {message}')


def on_message2(message):
    print(f'on message2: {message}')


class TestRedisPubSub:
    @pytest.mark.asyncio
    async def test_subscribe(self, pubsub: RedisPubSub):
        assert pubsub.current_sub_id == 0
        assert pubsub.subscriptions == {}

        await pubsub.subscribe('trigger1', on_message1)
        assert pubsub.current_sub_id == 1
        assert pubsub.subscriptions[1] == 'trigger1'

        await pubsub.subscribe('trigger1', on_message2)
        assert pubsub.current_sub_id == 2
        assert pubsub.subscriptions[1] == 'trigger1'
        assert pubsub.subscriptions[2] == 'trigger1'

        await pubsub.disconnect()

    @pytest.mark.asyncio
    async def test_unsubscribe(self, pubsub: RedisPubSub):
        sub_id = await pubsub.subscribe('trigger1', on_message1)

        await pubsub.unsubscribe(sub_id)
        assert sub_id not in pubsub.subscriptions

        await pubsub.disconnect()

    @pytest.mark.asyncio
    async def test_publish(self, pubsub: RedisPubSub, capsys):
        await pubsub.subscribe('trigger1', on_message1)

        await pubsub.publish('trigger1', {'hello': 'world'})
        await asyncio.sleep(0.1)
        captured = capsys.readouterr()
        assert captured.out == "on message1: {'hello': 'world'}\n"

        await pubsub.subscribe('trigger1', on_message2)

        await pubsub.disconnect()

    @pytest.mark.asyncio
    async def test_async_iterator(self, pubsub: RedisPubSub, capsys):
        iterator = pubsub.async_iterator('trigger')

        async def publish():
            await asyncio.sleep(0.1)
            await pubsub.publish('trigger', {'hello': 'world'})
            await pubsub.publish('trigger', {'hello': 'world'})

        asyncio.create_task(publish())
        assert await iterator.__anext__() == {'hello': 'world'}
        assert await iterator.__anext__() == {'hello': 'world'}

        await pubsub.disconnect()
