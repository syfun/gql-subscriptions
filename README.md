# gql-subscriptions

A Python3.7+ port of [Apollo Graphql Subscriptions](https://github.com/apollographql/graphql-subscriptions).

This package contains a basic asyncio pubsub system which should be used only in demo, and other pubsub system(like Redis).

## Requirements

Python 3.7+

## Installation

`pip install gql-subscriptions`

> This package should be used with a network transport, for example [starlette-graphql](https://github.com/syfun/starlette-graphql)

## Getting started with your first subscription

To begin with GraphQL subscriptions, start by defining a GraphQL Subscription type in your schema:

```
type Subscription {
    somethingChanged: Result
}

type Result {
    id: String
}
```

Next, add the Subscription type to your schema definition:

```
schema {
  query: Query
  mutation: Mutation
  subscription: Subscription
}
```

Now, let's create a simple `PubSub` instance - it is simple pubsub implementation, based on `asyncio.Queue`.

```python
from gql_subscriptions import PubSub

pubsub = PubSub()
```

Now, implement your Subscriptions type resolver, using the `pubsub.async_iterator` to map the event you need(use [python-gql](https://github.com/syfun/python-gql)):

```python
from gql_subscriptions import PubSub, subscribe


pubsub = PubSub()

SOMETHING_CHANGED_TOPIC = 'something_changed'


@subscribe
async def something_changed(parent, info):
    return pubsub.async_iterator(SOMETHING_CHANGED_TOPIC)
```

Now, the GraphQL engine knows that `somethingChanged` is a subscription, and every time we use pubsub.publish over this topic - it will publish it using the transport we use:

```
pubsub.publish(SOMETHING_CHANGED_TOPIC, {'somethingChanged': {'id': "123" }})
```

>Note that the default PubSub implementation is intended for demo purposes. It only works if you have a single instance of your server and doesn't scale beyond a couple of connections. For production usage you'll want to use one of the [PubSub implementations](#pubsub-implementations) backed by an external store. (e.g. Redis).

## Filters

When publishing data to subscribers, we need to make sure that each subscriber gets only the data it needs.

To do so, we can use `with_filter` decorator, which wraps the `subscription resolver` with a filter function, and lets you control each publication for each user.

```
ResolverFn = Callable[[Any, Any, Dict[str, Any]], Awaitable[AsyncIterator]]
FilterFn = Callable[[Any, Any, Dict[str, Any]], bool]

def with_filter(filter_fn: FilterFn) -> Callable[[ResolverFn], ResolverFn]
    ...
```

`ResolverFn` is a async function which returned a `typing.AsyncIterator`.
```
async def something_changed(parent, info) -> typing.AsyncIterator
```

`FilterFn` is a filter function, executed with the payload(published value), operation info, arugments, and must return bool.

For example, if `something_changed` would also accept a argument with the ID that is relevant, we can use the following code to filter according to it:

```python
from gql_subscriptions import PubSub, subscribe, with_filter


pubsub = PubSub()

SOMETHING_CHANGED_TOPIC = 'something_changed'


def filter_thing(payload, info, relevant_id):
    return payload['somethingChanged'].get('id') == relevant_id


@subscribe
@with_filter(filter_thing)
async def something_changed(parent, info, relevant_id):
    return pubsub.async_iterator(SOMETHING_CHANGED_TOPIC)
```

## Channels Mapping

You can map multiple channels into the same subscription, for example when there are multiple events that trigger the same subscription in the GraphQL engine.

```python
from gql_subscriptions import PubSub, subscribe, with_filter

pubsub = PubSub()

SOMETHING_UPDATED = 'something_updated'
SOMETHING_CREATED = 'something_created'
SOMETHING_REMOVED = 'something_removed'


@subscribe
async def something_changed(parent, info):
    return pubsub.async_iterator([SOMETHING_UPDATED, SOMETHING_CREATED, SOMETHING_REMOVED])
```

## PubSub Implementations

It can be easily replaced with some other implements of [PubSubEngine abstract class](https://github.com/syfun/gql-subscriptions/blob/master/gql_subscriptions/engine.py).

This package contains a `Redis` implements.

```python
from gql import subscribe
from gql_subscriptions.pubsubs.redis import RedisPubSub


pubsub = RedisPubSub()

SOMETHING_CHANGED_TOPIC = 'something_changed'


@subscribe
async def something_changed(parent, info):
    return pubsub.async_iterator(SOMETHING_CHANGED_TOPIC)
```

You can also implement a `PubSub` of your own, by using the inherit `PubSubEngine` from this package, this is a [Reids example](https://github.com/syfun/gql-subscriptions/blob/master/gql_subscriptions/pubsubs/redis.py).