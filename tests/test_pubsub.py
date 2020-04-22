import asyncio

import pytest

from gql_subscriptions.pubsub import EventEmitter, PubSub


@pytest.fixture()
def emitter(scope='function'):
    return EventEmitter()


def listener1():
    print('listener1 happened')


def listener2():
    print('listener2 happened')


def listener_with_args(*args):
    print(f'listener with args: {args}')


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

    @pytest.mark.asyncio
    async def test_emit_and_execute_listener(self, emitter: EventEmitter, capsys):
        emitter.add_listener('add', listener1)
        emitter.add_listener('add', listener2)
        emitter.add_listener('args', listener_with_args)

        await emitter.emit('add')
        await asyncio.sleep(0.1)
        captured = capsys.readouterr()
        assert captured.out == 'listener1 happened\nlistener2 happened\n'

        await emitter.emit('args', 1, 2)
        await asyncio.sleep(0.1)
        captured = capsys.readouterr()
        assert captured.out == 'listener with args: (1, 2)\n'

        await emitter.emit('args', 1)
        await asyncio.sleep(0.1)
        captured = capsys.readouterr()
        assert captured.out == 'listener with args: (1,)\n'

        await emitter.stop()

    @pytest.mark.asyncio
    async def test_stop(self, emitter: EventEmitter):
        await emitter.emit('add')
        assert emitter.queue
        assert not emitter.run_task.done()

        await emitter.stop()
        await asyncio.sleep(0.1)
        assert emitter.run_task.done()


@pytest.fixture()
def pubsub(scope='function'):
    return PubSub()


def on_message1(message):
    print(f'on message1: {message}')


def on_message2(message):
    print(f'on message2: {message}')


class TestPubSub:
    @pytest.mark.asyncio
    async def test_subscribe(self, pubsub: PubSub):
        assert pubsub.current_sub_id == 0
        assert pubsub.subscriptions == {}

        await pubsub.subscribe('trigger1', on_message1)
        assert pubsub.current_sub_id == 1
        assert pubsub.subscriptions == {1: ('trigger1', on_message1)}

        await pubsub.subscribe('trigger1', on_message2)
        assert pubsub.current_sub_id == 2
        assert pubsub.subscriptions == {1: ('trigger1', on_message1), 2: ('trigger1', on_message2)}

    @pytest.mark.asyncio
    async def test_unsubscribe(self, pubsub: PubSub):
        sub_id = await pubsub.subscribe('trigger1', on_message1)

        await pubsub.unsubscribe(sub_id)
        assert sub_id not in pubsub.subscriptions
        assert 'trigger1' not in pubsub.emitter.events

    @pytest.mark.asyncio
    async def test_publish(self, pubsub: PubSub, capsys):
        await pubsub.subscribe('trigger1', on_message1)

        await pubsub.publish('trigger1', {'hello': 'world'})
        await asyncio.sleep(0.1)
        captured = capsys.readouterr()
        assert captured.out == "on message1: {'hello': 'world'}\n"

        await pubsub.subscribe('trigger1', on_message2)

        await pubsub.publish('trigger1', {'hello': 'world'})
        await asyncio.sleep(0.1)
        captured = capsys.readouterr()
        assert captured.out == "on message1: {'hello': 'world'}\non message2: {'hello': 'world'}\n"

        await pubsub.emitter.stop()

    @pytest.mark.asyncio
    async def test_async_iterator(self, pubsub: PubSub, capsys):
        iterator = pubsub.async_iterator('trigger1')
        asyncio.create_task(pubsub.publish('trigger1', {'hello': 'world'}))
        asyncio.create_task(pubsub.publish('trigger1', {'hello': 'world'}))
        message = await iterator.__anext__()
        assert message == {'hello': 'world'}
        message = await iterator.__anext__()
        assert message == {'hello': 'world'}

        await pubsub.emitter.stop()
