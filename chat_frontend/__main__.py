import argparse

import aioredis
import logging.handlers

import asyncio

import uvloop
from aiohttp import web

from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import start_http_server

from chat_frontend.app import websocket_handler, healthcheck
from chat_frontend.room_service import RoomService

log = logging.getLogger(__name__)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=2000)
    ap.add_argument("--host", default='0.0.0.0')
    ap.add_argument("--redis_host", default='redis')
    ap.add_argument("--redis_port", type=int, default=6432)
    ap.add_argument("--mongo_host")
    ap.add_argument("--mongo_username", default='')
    ap.add_argument("--mongo_password", default='')
    ap.add_argument("--mongo_db", default='')
    ap.add_argument("--debug", default=False)
    return ap.parse_args()


async def create_redis_pool(redis_host='redis', redis_port='', pool_size=1):
    return await aioredis.create_redis_pool(
        address=f'redis://{redis_host}:{redis_port}',
        maxsize=pool_size
    )


def create_mongo_client(debug, mongo_host, mongo_username, mongo_password):
    auth = f"{mongo_username}:{mongo_password}@" if not debug else ''
    return AsyncIOMotorClient(
        f'mongodb://{auth}{mongo_host}'
    )


async def shutdown(app):
    for task in  app['tasks']:
        if not task.cancelled():
            task.cancel()
    redis_pool = app['redis_pool']
    redis_pool.close()
    await redis_pool.wait_closed()


async def create_frontend(args):
    redis_pool = await create_redis_pool(redis_host=args.redis_host, redis_port=args.redis_port)
    mongo_client = create_mongo_client(
        debug=args.debug,
        mongo_host=args.mongo_host,
        mongo_password=args.mongo_password,
        mongo_username=args.mongo_username
    )
    db = mongo_client[args.mongo_db]
    room_service = RoomService(redis=redis_pool, db=db)
    loop = asyncio.get_event_loop()
    tasks = (
        loop.create_task(room_service.listen_new_messages()),
        loop.create_task(room_service.ping_pong_task())
    )

    app = web.Application()
    app['db'] = db
    app['mongo_client'] = mongo_client
    app['tasks'] = tasks
    app['mongo_client'] = mongo_client
    app['room_service'] = room_service
    app['redis_pool'] = redis_pool

    app.router.add_route(
        'GET', '/ws', websocket_handler
    )

    app.router.add_route(
        'GET', '/health', healthcheck
    )
    app.on_shutdown.append(shutdown)
    return app


def main():
    args = parse_args()
    host = args.host
    port = args.port
    try:
        start_http_server(9100)
    except Exception as e:
        log.error(f'Prometheus client error, {e}')

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    log.info(f"Listening {host}:{port}")
    web.run_app(create_frontend(args), host=host, port=port)


if __name__ == '__main__':
    main()
