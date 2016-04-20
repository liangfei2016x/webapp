# 创建连接池
import asyncio
import logging
import aiomysql
import mysql.connector


def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# 异步IO：协程


@asyncio.coroutine
# Python允许你在list或tuple前面加一个*号，把list或tuple的元素变成可变参数传进去
#**kw是关键字参数，kw接收的是一个dict(key=values).
def create_pool(loop, **kw):
    logging.info('create database connection pool....')
    # global 全局变量
    global __pool
    __pool = yield from aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', '3306'),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', '10'),
        minsize=kw.get('minsize', '1'),
        loop=loop
    )

# select sql


@asyncio.coroutine
def select(sql, args, size=None):
    logging.log(sql, args)
    global __pool
    # Python对with的处理。基本思想是with所求值的对象必须有一个__enter__()方法，一个__exit__()方法。
    with (yield from __pool) as conn:
        # cursor 游标：通过cursor来执行sql语句
        cur = yield from conn.cursor(aiomysql.DictCursor)
        # execute(self, query, args):执行单条sql语句,接收的参数为sql语句本身和使用的参数列表,返回值为受影响的行数
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            # fetchmany(self, size=None):接收size条返回结果行.如果size的值大于返回的结果行的数量,
            # 则会返回cursor.arraysize条数据.
            rs = yield from cur.fetchmany(size)
        else:
            # fetchall(self):接收全部的返回结果行.
            rs = yield from cur.fetchall()
        # 关闭连接对象
        yield from cur.close()
        logging.info('rows returned:%s' % len(rs))
        return rs

# insert update delete (sql) 返回结果是行数


def excute(sql, args):
    logging.log(args)
    with (yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
            # raise显示地引发异常。一旦执行了raise语句，raise后面的语句将不能执行。
            raise
        return affected


def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ','.join(L)


def Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s,%s:%s>' % (self.__class__.__name__, self.column_type, self.primary_key, self.name)


class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntegerField(Field):

    def __init__(self, name=None, primary_key, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table:%s)' % (name, tableName))
        mappings = dict()
        fields = []
        primary_key = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('found mapping:%s==>%s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primaryKey:
                        raise StandarError(
                            'Duplicate primary key for field:%s' % k)
                    primaryKey = k
                else:
                    field.append(k)
                if not primaryKey:
                    raise StandarError('Primary key not found.')
                for k in mapping.keys():
                    attrs.pop(k)
                escaped_fields = list(Map(lambda f: '%s' % f, fields))
                attrs['__mappings__'] = mappings
                attrs['__table__'] = tableName
                attrs['__primary_key__'] = primaryKey
                attrs['__fields__'] = fields
                attrs['__select__'] = 'select ' % s', %s from ' % s'' % (primaryKey, ','.join(escaped_fields), tableName)
                attrs['__insert__'] = 'insert into ' % s' (%s,%s) values(%s)' % (tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields)+1))
                attrs['__update__'] = 'update ' % s' set %s where ' % s'=?' % (tableName, ','.join(map(lambda f: '' % s'=?' % (mapping.get(f).name or f), fields)), primaryKey)
                attrs['__delete__'] = 'delete from ' % s' where ' % s'=?' % (tableName, primaryKey)
                return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[Key]
        except KeyError:
            raise AttributeError(
                r" 'model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(
                    field.default) else field.default
                logging.debug('using default value for %s: %s' %
                              (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause.'
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?,?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % s str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        'find number by select and where'
        sql = ['selec %s _num_from ' % s'' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    async def find(cls, pk):
        ' find object by primary key'
        rs = await select(' %s where ' % s'=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record:affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn(
                ' failed to update by primary key:affected rows: %s' % rows)
    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn(
                ' failed to remove by primary key:affected rows:%s' % rows)
