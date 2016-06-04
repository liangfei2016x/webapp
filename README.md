# webapp
博客管理系统


运用技术：


Python 3.5 + mysql（数据库）+uikit框架（web前端、CSS框架）.


编辑器：PyCharm 或 sublime Text3


模块：


	异步框架：asynico.


	协程，又称微线程，纤程。英文名Coroutine


	Asynico是Python 3.4的标准库，直接内置了对异步的IO。异步操作需要在coroutine中通过yield from 完成。


前端模板引擎：jinja2.

MVC模式：Model:数据(python)
		View:负责显示逻辑（HTML）
		Controller:负责业务逻辑(python)


ORM(对象关系映射):


创建连接池：异步协程aiomysql.create_pool(pool)


Select(查询)：通过fetchmany()获得最多条数记录，通过fetchall()获得所有记录


Insert(增),Delete(删),Update(改):可以定义execute()函数，因为这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数rowcount。


定义Model：从dict继承 拥有dict的 __getattr__()和__setattr__()方法


定义Filed(表)和Field子类。


Model只是一个基类，通过metaclass(元类) 读取子类的映射信息。在再Model类里面添加


save(),remove(),update()调用execute()、find(),findAll(),findNumber()调用select()等方法。


app.py:处理url 的请求(reques),响应(response),假如是post请求需要对数据进行处理(Json)。
Coroweb.py:解析URL。
Handlers.py:发送请求 返回模板

如果一个URL返回的不是HTML，而是机器能直接解析的数据，这个URL就可以看成是一个Web API 也就是说主要用来传输数据

MVVM最早是有微软提出来的，借鉴了桌面应用程序的MVC思想，在前端页面中，Model用纯JavaScript对象表示，View用纯HTML 表示。
VM需要用JavaScript编写一个通用的ViewModel。

本项目中用的是VUE 这个MVVM框架来实现。
