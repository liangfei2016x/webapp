#创建连接池
import  asyncio,logging,aiomysql
import mysql.connector
#异步IO：协程
@asyncio.coroutine
#Python允许你在list或tuple前面加一个*号，把list或tuple的元素变成可变参数传进去
#**kw是关键字参数，kw接收的是一个dict(key=values).
def create_pool(loop,**kw):
    logging.info('create database connection pool....')
    #global 全局变量
    global __pool
    __pool = yield from aiomysql.create_pool(
    host = kw.get('host','localhost'),
    port = kw.get('port','3306'),
    user = kw['user'],
    password = kw['password'],
    db = kw['db'],
    charset= kw('charset','utf8'),
    autocommit = kw.get('autocommit',True),
    maxsize = kw.get('maxsize','10'),
    minsize = kw.get('minsize','1'),
    loop=loop
    )

#select sql
@asyncio.coroutine
def select(sql,args,size=None):
    logging.log(sql, args)
    global __pool
    #Python对with的处理。基本思想是with所求值的对象必须有一个__enter__()方法，一个__exit__()方法。
    with (yield from __pool) as conn:
        #cursor 游标：通过cursor来执行sql语句
        cur = yield from conn.cursor(aiomysql.DictCursor)
        #execute(self, query, args):执行单条sql语句,接收的参数为sql语句本身和使用的参数列表,返回值为受影响的行数
        yield from cur.execute(sql.replace('?','%s'),args or ())
        if size:
            #fetchmany(self, size=None):接收size条返回结果行.如果size的值大于返回的结果行的数量,
            # 则会返回cursor.arraysize条数据.
            rs = yield from cur.fetchmany(size)
        else:
            #fetchall(self):接收全部的返回结果行.
            rs = yield from cur.fetchall()
        #关闭连接对象
        yield from cur.close()
        logging.info('rows returned:%s' % len(rs))
        return rs

#insert update delete (sql) 返回结果是行数
def excute(sql,args):
    logging.log(args)
    with (yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?','%s'),args)
            affected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
        #raise显示地引发异常。一旦执行了raise语句，raise后面的语句将不能执行。
            raise
        return  affected