import logging; logging.basicConfig(level=logging.INFO)
import sys
import asyncio, os, json, time
from datetime import datetime

from aiohttp import web #aiohttp.web 会自动创建 Request 实例
#Environment是Jinja2中的一个核心类，它的实例用来保存配置、全局对象，以及从本地文件系统或其它位置加载模板。
#FileSystemLoader:文件系统加载器，他可以从本地文件系统中查找并加载模块。
from jinja2 import Environment, FileSystemLoader

import webapp.www.orm
from webapp.www.coroweb import add_routes, add_static
#使用jinja2模块为app 添加env环境对象：
def init_jinja2(app, **kw):
    #打印日志
    logging.info('init jinja2...')
    #获取方法传递的参数 并组成dict 形式
    options = dict(
        #autoescape xml/html自动转义，缺省值为false 就是在渲染模块时候自动把变量中的<>&等字符转换为&lt;&gt;&amp
        autoescape = kw.get('autoescape', True),#dict.get(key,default=None):返回指定的键值，如果值不在字典中返回默认值None
        block_start_string = kw.get('block_start_string', '{%'),#块开始标记符，缺省值是{%
        block_end_string = kw.get('block_end_string', '%}'),#块结束标记符，缺省值是%}
        variable_start_string = kw.get('variable_start_string', '{{'),#变量开始标记符，缺省值 {{
        variable_end_string = kw.get('variable_end_string', '}}'),#变量结束标记符，缺省值}}
        auto_reload = kw.get('auto_reload', True)#设为Ture jinja2会在使用template时检查模板文件的状态，如果文件有修改则重新加载
    )
    path = kw.get('path', None)
    if path is None:
        #os.path.abspath(__file__):返回当前脚本的绝对路径(包括文件名)
        #os.path.dirname():去掉文件名，返回目录路径
        #os.path.jion():将各个部分组成一个路径名
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    #jiajn2.Environment():创建模板环境和制定文件夹中寻找模板加载器
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)#环境的过滤器字典
    #若过滤器不为None,将环境中的过滤器名字循环出来，添加到新的env环境对象的过滤器字典中：
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env
#middlewares请求响应处理器-日志处理器：
#记录URL日志：
@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):#不需要手动创建 Request 实例，aiohttp.web会自动生成
        logging.info('Request: %s %s' % (request.method, request.path))
        # await asyncio.sleep(0.3)
        return (yield from handler(request))
    return logger

#middlewares请求服务器响应-数据处理器
@asyncio.coroutine
def data_factory(app, handler):
    @asyncio.coroutine
    def parse_data(request):
        #若请求方法是POST
        if request.method == 'POST':
            #若POST请求的实体MIME类型是以application/json 开头
            if request.content_type.startswith('application/json'):
                #以json编码读取请求内容：
                request.__data__ = yield from request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                #读取请求内容的post参数
                request.__data__ = yield from request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (yield from handler(request))
    return parse_data
#请求响应处理器
@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info('Response handler...')
        r = yield from handler(request)
        #若是HTTP响应处理类型，则返回
        if isinstance(r, web.StreamResponse):
            return r
        #若是bytes类型
        if isinstance(r, bytes):
            #web.Response().继承StreamResponse,接收参数来设置HTTP响应体
            resp = web.Response(body=r)
            #设置实体MIME类型
            resp.content_type = 'application/octet-stream'
            return resp
        #若是str类型
        if isinstance(r, str):
            if r.startswith('redirect:'):
                #切片处理r,返回重定向结果 从下标9以后的结果
                return web.HTTPFound(r[9:])
            #若不是以redirect开头，则进行以下设置
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        #若是dict(字典)类型
        if isinstance(r, dict):
            #获取字典中env环境对象
            template = r.get('__template__')
            if template is None:
                #json.dumps()以JSON编码格式转换python对象，返回一个str.ensure_ascii:非ASCII字符不转换，原样输出
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                #设置MIME类型
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                #取出cookie用户信息绑定到request对象：
               # r['__user__'] = request.__user__
                #jinja2.Template.render():返回模板unicode字符串
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        #若以上的条件都为满足，默认返回resp赋值方式：
        # default:
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response

def datetime_filter(t):
    # time.time()：返回当前时间的时间戳(1970后经过的秒数)，浮点类型。
    delta = int(time.time() - t)#获取时间差
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    #返回本地平台的日期时间对象
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)
@asyncio.coroutine
def init(loop):
    yield from webapp.www.orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password='123456', db='awesome')
    print("链接数据库")
    app = web.Application(loop=loop, middlewares=[
        logger_factory, response_factory
    ])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()