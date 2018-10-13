#!/usr/bin/env python

# WS server example that synchronizes state across clients

import asyncio
import json
import websockets
import time

STATE = {'value': 0}
USERS = set()
connected = dict()
chat = list()


def state_event():
    return json.dumps({'type': 'state', **STATE})


def users_event():
    return json.dumps({'type': 'users', 'count': len(USERS)})


async def notify_state():
    if USERS:       # asyncio.wait doesn't accept an empty list
        message = state_event()
        await asyncio.wait([user.send(message) for user in USERS])


async def notify_users():
    if USERS:       # asyncio.wait doesn't accept an empty list
        message = users_event()
        await asyncio.wait([user.send(message) for user in USERS])


async def register(websocket):
    USERS.add(websocket)
    # await notify_users()
    await show_users()


async def unregister(websocket):
    USERS.remove(websocket)
    # await notify_users()
    await show_users()


# ---------------------------------
async def show_users():
    if USERS:
        # print(connected.values())
        message = json.dumps({'type': 'users', 'users': ', '.join(connected.values())})
        await asyncio.wait([user.send(message) for user in USERS])


async def replay_chat(user_in, user_to):
    for _tm, _in, _to, _msg in chat:
        if user_in == _in and user_to == _to or user_in == _to and user_to == _in:
            data_js = json.dumps({'type': 'chat', 'name': _in, 'user_to': _to, 'msg': _msg})
            await asyncio.wait([ws.send(data_js) for ws, user in connected.items() if user == user_in])


async def message_to(user_in, user_to, msg):

    chat.append(
        (str(time.time()), user_in, user_to, msg)
    )

    for ws, user_name in connected.items():
        if user_name == user_to:
            # data = await show_chat(user_name)
            data_js = json.dumps({'type': 'chat', 'name': user_in, 'user_to': user_to, 'msg': msg})
            await asyncio.wait([ws.send(data_js) for ws, user in connected.items() if user == user_to or user == user_in])


async def show_chat(user_in):
    chat_local = []
    js_data = ''
    for tm, _in, _out, _msg in chat:
        chat_local.append(';'.join([tm, _in, _out, _msg]))
        if _in == user_in:
            print(f'>{_in}:{_msg}')

        if _out == user_in:
            print(f'< |------------{_in}:{_msg}')

    return chat_local


async def add_user(websocket, name):
    found = False
    if connected:
        for ws, name_ws in connected.items():
            if name_ws == name:
                found = True
                break

    if found:
        del connected[ws]

    connected[websocket] = name
    await show_users()


async def remove_user(websocket):
    del connected[websocket]
    await show_users()


async def producer(websocket, path):
    # register(websocket) sends user_event() to websocket
    await register(websocket)

    try:
        await websocket.send(state_event())
        async for message in websocket:
            if message:
                data = json.loads(message)

                if data['action'] == 'connect':
                    await add_user(websocket, data['name'])

                elif data['action'] == 'disconnect':
                    await remove_user(websocket)

                elif data['action'] == 'message_to':
                    await message_to(user_in=data['name'], user_to=data['user_to'], msg=data['message'])

                elif data['action'] == 'replay':
                    await replay_chat(user_in=data['name'], user_to=data['user_to'])

                else:
                    print("WTF: {}", data)

    finally:
        await unregister(websocket)

asyncio.get_event_loop().run_until_complete(websockets.serve(producer, 'localhost', 6789))
asyncio.get_event_loop().run_forever()
