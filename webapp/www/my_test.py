import sys
import webapp.www.orm
from webapp.www.models import User, Blog, Comment
import asyncio

def test(loop):
    print('我我',loop)
    yield from webapp.www.orm.create_pool(loop=loop,user='root', password='123456', db='awesome')

    u = User(name='Test', email='test8@example.com', passwd='1234567890', image='about:blank',created_at=3)
    print('我', u)
    yield from u.save()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
    loop.close()
    if loop.is_closed():
        sys.exit(0)