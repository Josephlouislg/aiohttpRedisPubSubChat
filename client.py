import asyncio
import json
import os

import aiohttp

HOST = os.getenv('HOST', 'example.com')
PORT = int(os.getenv('PORT', 80))

URL = f'http://{HOST}:{PORT}/ws'


async def main():
    session = aiohttp.ClientSession()
    async with session.ws_connect(URL) as ws:

        await ws.send_str((json.dumps({"type": "subscribe", "channel_id": 3})))
        await prompt_and_send(ws)
        async for msg in ws:
            print('Message received from server:', msg)
            if msg.type in (aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR):
                break


async def prompt_and_send(ws):
    msg = 'ping'
    new_msg_to_send = json.dumps({"type": "publish", "channel_id": 3, "text": msg})
    await ws.send_str(new_msg_to_send)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
