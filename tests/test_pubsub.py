import pytest
from gql_subscriptions.pubsub import PubSubEngine, EventEmitter


@pytest.fixture()
async def emitter(scope='function'):
    emitter = EventEmitter()
    yield emitter
    await emitter.stop()


def listener1():
    print('listener1 happened')


def listener2():
    print('listener2 happened')


class TestEventEmitter:

    @pytest.mark.asyncio
    async def test_add_listener(self, emitter: EventEmitter):
        emitter.add_listener('add', listener1)
        assert emitter.events['add'] == {hash(listener1): listener1}

        emitter.add_listener('add', listener2)
        assert emitter.events['add'] == {hash(listener1): listener1, hash(listener2): listener2}

    @pytest.mark.asyncio
    async def test_remove_listener(self, emitter: EventEmitter):
        emitter.add_listener('add', listener1)
        emitter.add_listener('add', listener2)

        emitter.remove_listener('add', listener1)
        assert emitter.events['add'] == {hash(listener2): listener2}

        emitter.remove_listener('add', listener2)
        assert 'add' not in emitter.events
