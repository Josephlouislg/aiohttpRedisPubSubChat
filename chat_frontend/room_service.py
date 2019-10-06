import json
import logging

import asyncio

from motor.motor_asyncio import AsyncIOMotorDatabase


log = logging.getLogger(__name__)


class RoomService(object):
    def __init__(self, db: AsyncIOMotorDatabase, redis, redis_msg_channel='redis_broadcast:1'):
        self._redis = redis
        self._chanels_connections = {}
        self._redis_msg_channel = redis_msg_channel
        self._db = db

    async def _create_channel(self, channel_id):
        channel_exists = await self._db.channels.find_one(
            {"channel_id": channel_id}, {"_id": 1}
        )
        if not channel_exists:
            await self._db.channels.insert_one({
                "channel_id": channel_id,
                "messages": []
            })

    async def _create_message(self, message, channel_id):
            await self._db.channels.update_one(
                {"channel_id": channel_id},
                {"$push": {"messages": message}}
            )

    async def subscribe(self, channel_id, connection):
        if self._chanels_connections.get(channel_id):
            self._chanels_connections[channel_id].add(connection)
        else:
            self._chanels_connections[channel_id] = {connection}
            await asyncio.shield(self._create_channel(channel_id))

    async def unsubscribe(self, connection):
        for connections in self._chanels_connections.values():
            connections.discard(connection)
        if not connection.closed:
            await connection.close()

    async def ping_pong_task(self):
        while True:
            for room_connections in self._chanels_connections.values():
                for connection in room_connections:
                    try:
                        connection.send_str(json.dumps({
                            "type": "ping"
                        }))
                    except Exception:
                        await self.unsubscribe(connection)
            await asyncio.sleep(5)

    async def listen_new_messages(self):
        channel, *_ = await self._redis.subscribe(self._redis_msg_channel)
        async for raw in channel.iter():
            try:
                msg = json.loads(raw)
                connections = self._chanels_connections.get(msg['channel_id'], ())
                for connection in connections:
                    try:
                        await connection.send_str(json.dumps(msg))
                    except Exception:
                        await self.unsubscribe(connection)
            except Exception as e:
                log.error(e)

    async def push_message(self, channel_id, msg):
        await asyncio.shield(self._create_message(message=msg, channel_id=channel_id))
        message = json.dumps({
            "channel_id": channel_id,
            "text": msg
        })
        await self._redis.publish(self._redis_msg_channel, message)
