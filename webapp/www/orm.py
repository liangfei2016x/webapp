# 创建连接池
import asyncio
import logging
import aiomysql


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
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )

# select sql
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
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

# insert update delete (sql) 的执行都需要相同的参数，以及返回一个整数影响的行数
#因此封装在一个函数（execute）中
def execute(sql, args):
    log(args)
    with (yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args or ())
            #返回影响的行数
            affected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
            # raise显示地引发异常。一旦执行了raise语句，raise后面的语句将不能执行。
            raise
        return affected

#构造占位符 why？
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ','.join(L)

#父类(域)，可被其他域继承
class Field(object):
    #域的初始化，有属性名，属性列（属性类型），是否主键，
    #default参数允许orm自己填缺省值，具体看具体的类怎么使用

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
    #一次输出 类名，属性类型，主键，属性名
    def __str__(self):
        return '<%s,%s:%s>' % (self.__class__.__name__, self.column_type,self.name)

#字符串域
class StringField(Field):
    #ddl(data definition languages) 定义数据类型
    #varchar 可变的数据类型 长度范围为：0~100
    #char 不可变的数据类型  不够默认用空格补充
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

#布尔域
class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

#整数域
class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

#浮点域
class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

#文本域
class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

#这是一个元类,它定义了如何来构造一个类，任何定义了__metaclass__属性域制定了metaclass的类都会通过元类构造方法来构造类
#任何继承自Model类，都会自动同ModelMetaclass扫描映射关系，并存储到自身的类属性中
class ModelMetaclass(type):
    #cls创建类对象。相当于self
    #name:类的名字，例如user类，student类，创建时：name=user
    #bases:父类的元组
    #attrs:父类（方法）的字典，比如User有__table__,id等，就作为attrs的keys
    def __new__(cls, name, bases, attrs):
        #排除Model本身，因为本来Model就是用来被继承的，其不存在与表的映射关系
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        #获得表名 如果没有__table__属性 则类名为表名 (or 的用法）
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table:%s)' % (name, tableName))
        #获取所有的Field和主键名 存放在dict中
        mappings = dict()#用来存储属性名与数据库表列(数据类型)的映射关系
        fields = []#用来存储非主键的属性
        primaryKey = None#用来保存主键
        for k, v in attrs.items():
            if isinstance(v, Field):
                #找到映射关系
                logging.info('found mapping:%s==>%s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primaryKey:#假如主键已经存在，又找到一个主键，则报错
                        raise RuntimeError('Duplicate primary key for field:%s' % k)
                    primaryKey = k
                else:
                    #将非主键添加到fields中
                    fields.append(k)
        #一张表没有主键也报错
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
                #删除重复的键值
        for k in mappings.keys():
            attrs.pop(k)
                #将非主键存放在escaped中：list类型，方便增删改查
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings#保存属性和列的映射关系
        attrs['__table__'] = tableName#保存表名
        attrs['__primary_key__'] = primaryKey#保存主键
        attrs['__fields__'] = fields#保存非主键
        attrs['__select__'] = 'select `%s`, %s from `%s`' %  (primaryKey, ','.join(escaped_fields), tableName)
        #利用create_args_string生成若干个占位符。（不懂）
        attrs['__insert__'] = 'insert into  `%s` (%s,`%s`) values(%s)' % (tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields)+1))
        attrs['__update__'] = 'update `%s` set %s where  `%s`=?' % (tableName, ','.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

#定义所有orm的基类Model
#Model继承dict,所具有dict的所有功能，又实现了特殊的get和set方法。
#因此又可以像引用普通字段一样：a['arg']或a.args
class Model(dict, metaclass=ModelMetaclass):
    #初始化参数，调用父类（dict）的方法
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)
    #获取属性方便 a.args
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r" 'model' object has no attribute '%s'" % key)
    #设置属性方便 a.args
    def __setattr__(self, key, value):
        self[key] = value
    #通过key取值，若不存在则返回None
    def getValue(self, key):
        return getattr(self, key, None)
    #通过key取值，若不存在则返回默认值
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]#field是一个定义域！比如floatField
            if field.default is not None:
                #id的StringField.default=next_id,因此调用该函数生成独立id
                #FloatField.default=time.time.返回当前时间
                #普通属性的StringField默认为None,因此还返回None
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' %(key, str(value)))
                #通过default设置value的值然后返回
                setattr(self, key, value)
        return value
    @classmethod
    async def  find(cls,pk):
        'find object by primary key'
        rs=await select('%s where `%s`=?' % (cls.__select__,cls.primary_key,[pk],1))
        if len(rs) == 0:
            return None
        return cls(**rs[0])
    @classmethod
    @asyncio.coroutine
    def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause.'
        #我们定义的默认select是通过主键查询的，并不包括where，orderBy,limit等关键字
        #假如存在关键字,就在select语句中增加关键字
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
         #orderBy
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
         #limit
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
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = yield from select(' '.join(sql), args)
        print('我',rs)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        'find number by select and where'
        sql = ['selec %s _num_from `% s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']
    @asyncio.coroutine
    def save(self):
        print('执行save')
        args = list(map(self.getValueOrDefault, self.__fields__))
        print(args[1])
        args.append(self.getValueOrDefault(self.__primary_key__))
        #调用插入语句
        rows =yield from execute(self.__insert__, args)
        #插入一条记录，结果影响的条数不为1，则报错
        if rows != 1:
            logging.warn('failed to insert record:affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn(' failed to update by primary key:affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]#取得主键作为参数
        rows = await execute(self.__delete__, args)#调用默认的delete语句
        if rows != 1:
            logging.warn('failed to remove by primary key:affected rows:%s' % rows)