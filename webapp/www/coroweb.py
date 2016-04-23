import asyncio,os,inspect,logging,functools
from urllib import parse
from aiohttp import web
from webapp.www.apis import APIError
#get和post是修饰方法，主要是为对象加上'__method__'和'__route__'属性
#通过@get()函数附带url信息
def get(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__='GET'
        wrapper.__route__=path
        return wrapper
    return decorator
#通过@past()附带url信息
def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__='POST'
        wrapper.__route__=path
        return wrapper
    return decorator
#inspect.Parameter的Kind类型有五种：
#POSITION_ONLY  只能是位置参数a(x)
#POSITIONAL_OR_KEYWORD 关键字参数或位置参数 **kw或a(x)
#VAR_POSITIONAL 相当于可变参数 *arg
#KEYWORD_ONLY   必须提供价值作为一个关键字参数,关键字只有参数是那些*或*args条目后出现一个Python函数定义。及命名关键字参数
#VAR_KEYWORD  相当于关键字参数 **kw

#获取函数传递值中命名关键字参数(不包含缺省值的)名称列表
def get_required_kw_args(fn):
    args=[]
    #inspect.signature(fn):调用fn函数的签名及注释，为函数提供一个parameter对象存储参数集合。
    #inpect.signature(fn).parameters.：返回参数名(name)与参数对象（param）对象的有序集合
    params = inspect.signature(fn).parameters
    for name, param in params.items():#items()返回一个由tuple(name,param)组成的list对象
        #param.default ：参数的缺省值，如果没有则属性被设置成Parameter.empty
        if param.kind==inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)
#获取函数传递值中命名关键字参数(全部的)名称列表：
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)
#判断函数传递中是否有命名关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True
#如果url处理函数的参数是**kw,则返回**kw
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True
#如果url处理的函数的参数是 request 则返回True
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name,param in params.items():
        if name == 'request':
            found = True
            continue
        # 传递值中包含参数名为'request'的参数，且参数值对应到传参列表方式不是“可变参数*args、关键参数**kw、命名关键字参数（*，a,b)”中的任意一种，则抛出异常：
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_POSITIONAL):
            raise ValueError('request parameter must be the last named parameter in function:%s%s'% (fn.__name__,str(sig)))
            return found
#用RequestHandler()来封装一个URL处理函数
class RequestHandler(object):
    #初始化已实例化后的所有父类对象，方便后续使用或扩展父类中的行为：
    def __init__(self, app,fn):
        self._app=app
        self._func=fn
        #判断url的参数类型
        self._has_request_arg=has_request_arg(fn)#参数是request 返回Ture
        self._has_var_kw_arg=has_var_kw_arg(fn)#参数包含关键字参数 返回Ture
        self._has_named_kw_args=has_named_kw_args(fn)#参数包含命名关键字参数
        self._named_kw_args=get_named_kw_args(fn)#参数包含命名参数(全部的)名称列表
        self._required_kw_args=get_required_kw_args(fn)#参数包含命名关键字参数（不含默认设置缺省值）列表
#__call__函数就是从URL中分析其需要接收的函数的参数，结果转换为web.Response对象
    async def __call__(self,request):
        kw = None
        #判断函数是否包含"可变参数，命名关键字参数、关键字参数"，以及能否获得参数(不含缺省)名称列表：
        if self._has_ver_kw_arg or self.has_named_kw_args or self._required_kw_args:
            #假如HTTP的请求类型是POST
            if request.method == 'POST':
                #判断Content-type标明发送或者接收的实体类型的mime类型，如：Content-Type:text/html 是否存在
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                    #改成小写
                    ct = request.content_type.lower()
                #判断ct字符串是否以'application/json'开头
                if ct.startswith('application/json'):
                    #以JSON编码读取请求内容
                    params = await request.json()#request.json()是协程
                    #判断params是否为dict类型
                    if not isintance(params,dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw =params
                elif ct.startswith('application/x-www-form-urlencoded')or ct.startswith('multipart/form-data'):
                    #读取请求的内容的PSOT参数
                    params = await request.post()
                    #构造PSOT字典
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-type:%s' % request.content_type)
            #假如请求方法是GET
            if request.method == 'GET':
                #获取请求中的字符串
                qs=request.query_string
                if qs:
                    #把qs以dict()形式存储起来，并赋值给kw
                    kw = dict()
                    # urllib.parse.parse_qs(str)：返回解析指定字符串中的查询字符串数据字典；可选参数值“True”表示空白值保留为空白字符串，默认为忽略(False)。
                    for k, v in parse.parse_qs(qs,True).items():
                        kw[k] = v[0]
        # 如果kw为空得话，kw设置为request.match_info
        if kw is None:
            #request.match_info:地址的解析结果。(只读属性和抽象匹配信息实例)
            kw = dict(**request.match_info)
        else:
            #若函数不包括关键字参数和命名关键字参数
            if not self.has_var_kw_arg and self._named_kw_args:
                copy = dict()
                #循环出参数的循环列表
                for name in self._named_kw_args:
                    if name in kw:
                        #并组成字典
                        copy[name] = kw[name]
                    kw = copy
                #从match_info中筛选出url需要传入的参数对
                for k, v in request.match_info.items():
                    if k in kw:
                        logging.warning('Duplicate arg name in named arg and kw args:%s'%k)
                        kw[k] = v
            #如果参数需要传入'request'参数，则把request实例传入
            if self._has_request_arg:
                kw['request'] = request
            #如果参数有默认的None的关键字参数，则遍历下kw
            if self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argment:%s' % name)
            logging.info('call with args:%s' % str(kw))
            try:
                #使用重构的kw参数字典，执行并返回结果集
                r = await self.func(**kw)
                return r
            except APIError as e:
                #返回自定义的异常信息分类及处理信息
                return dict(error=e.error,data=e.data,message=e.message)
#添加静态地址的处理函数：
def add_static(app):
    #os.path.dirname(path) 返回标准化的绝对路径
    #os.path.dirname(path):返回目录路径
    #os.path.join(path):将分离的各个部分组合成一个路径
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
    #aiohttp:web.Application.router:返回地址实例属性(只读)。
    #返回新的静态地址实例
    app.router.add_static('/static/',path)
    logging.info('add static %s=>%s'%('/static/',path))
#注册一个URL处理函数:
def add_route(app,fn):
    method = getattr(fn,'__method__',None)#获取请求方式。
    path = getattr(fn,'__route__',None)#获取地址信息。
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' %str(fn))
    #判断函数是否为协程函数且为生成器函数
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        #若不是协程函数(生成器函数)，则将其装饰成协程函数
        fn = asyncio.coroutine(fn)
    #inspect.singnature(fn):返回一个函数对象
    #inspect.singnature.parameters:返回对象参数的key值
    logging.info('add route %s %s => %s(%s)'%(method,path,fn.__name__,','.join(inspect.signature(fn).parameters.key())))
    #router返回地址实例,add_route并给地址添加响应方式、请求条件(请求地址、地址等。。)和对应的处理程序，返回给新的绝对地址和动态地址
    app.router.add_route(method,path,RequestHandler(app,fn))
#自动扫描、自动把Handler模块的所有符合条件的函数注册了
def add_routes(app,module_name):
    #str.rfind(str) 返回字符串最后一次出现的位置，没有则返回 -1
    n=module_name.rfind('.')
    if n ==(-1):
        #没有匹配 则导入"module_name模块"
        mod = __import__(module_name,globals(),locals())
    else:
        #切片 返回module_name模块中从'.'到末尾的字符串
        name = module_name[n+1:]

        mod =getattr(__import__(module_name[:n],globals(),locals(),[name]),name)
    # dir()：不带参数时，返回当前范围内的变量、方法和定义的类型列表；带参数时，返回参数的属性、方法列表。
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod,attr)
        if callable(fn):
            method = getattr(fn,'__method__',None)
            path = getattr(fn,'__route__',None)
            if method and path:
                add_route(app,fn)