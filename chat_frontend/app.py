import json
import logging.handlers

from aiohttp import web, WSMsgType

from chat_frontend.room_service import RoomService

log = logging.getLogger(__name__)


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    can_prepare = ws.can_prepare(request)
    room_service: RoomService = request.app['room_service']
    if not can_prepare.ok:
        rs = web.Response(status=400)
        rs.force_close()
        return rs
    await ws.prepare(request)

    try:
        async for ws_msg in ws:
            if ws_msg.type == WSMsgType.text:
                msg = json.loads(ws_msg.data)
                if msg['type'] == 'subscribe':
                    await room_service.subscribe(msg['channel_id'], ws)
                elif msg['type'] == 'publish':
                    await room_service.push_message(channel_id=msg['channel_id'], msg=msg['text'])
            elif ws_msg.type == WSMsgType.error:
                log.info('websocket closed with error')
                await room_service.unsubscribe(ws)
            elif ws_msg.type == WSMsgType.close:
                log.info('websocket closed normally')
                await room_service.unsubscribe(ws)
    finally:
        await room_service.unsubscribe(ws)
        return ws


async def healthcheck(request):
    return web.Response(status=200)
