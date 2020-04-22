import asyncio

import pytest

from gql_subscriptions.engine import PubSubAsyncIterator
from gql_subscriptions.pubsub import PubSub


@pytest.fixture()
def iterator(scope='function'):
    return PubSubAsyncIterator(PubSub(), ['trigger1', 'trigger2'])


class TestPubSubAsyncIterator:
    @pytest.mark.asyncio
    async def test_subscribe_all(self, iterator: PubSubAsyncIterator):
        assert await iterator.subscribe_all() == [1, 2]

    @pytest.mark.asyncio
    async def test_unsubscribe_all(self, iterator: PubSubAsyncIterator):
        ids = await iterator.subscribe_all()

        await iterator.unsubscribe_all(ids)
        assert iterator.pubsub.subscriptions == {}

    @pytest.mark.asyncio
    async def test_empty_queue(self, iterator: PubSubAsyncIterator):
        assert not iterator.all_subscribed
        iterator.all_subscribed = asyncio.create_task(iterator.subscribe_all())
        await iterator.all_subscribed
        assert iterator.all_subscribed.done()
        assert await iterator.all_subscribed == [1, 2]

        assert iterator.running
        await iterator.empty_queue()
        assert not iterator.running
        assert iterator.pubsub.subscriptions == {}

    @pytest.mark.asyncio
    async def test_pull_push_value(self, iterator: PubSubAsyncIterator):
        await iterator.push_value({'hello': 'world'})
        assert await iterator.pull_value() == {'hello': 'world'}

    @pytest.mark.asyncio
    async def test_anext(self, iterator: PubSubAsyncIterator):
        await iterator.push_value({'hello': 'world'})
        await iterator.push_value({'hello': 'world'})
        assert await iterator.__anext__() == {'hello': 'world'}
        assert await iterator.all_subscribed == [1, 2]
        assert await iterator.__anext__() == {'hello': 'world'}

        await iterator.aclose()

        with pytest.raises(StopAsyncIteration):
            await iterator.__anext__()
