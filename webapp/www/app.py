import logging; logging.basicConfig(level=logging.INFO)
#asyncio直接对异步IO的支持
import asyncio,os,json,time
from datetime import datetime

from aiohttp import web

def index(request):
    return web.Response(body=b'<h1>Awesome</h>')
#把一个generator标记为coroutine类型，然后把这个coroutine扔进EventLoop中执行
@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET','/',index)
    srv = yield from loop.create_server(app.make_handler(),'127.0.0.1',9000)
    logging.info('server started at http://127.0.0.1:9000..')
    return srv
#获取EventLoop事件
loop = asyncio.get_event_loop()
#执行coroutine事件
loop.run_until_complete(init(loop))
loop.run_forever()