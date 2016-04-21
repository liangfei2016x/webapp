import webapp.www.orm
from webapp.www.models import User, Blog, Comment

def test():
    yield from webapp.www.orm.create_pool(user='root', password='123456', database='awesome')

    u = User(name='Test', email='test@example.com', passwd='1234567890', image='about:blank')

    yield from u.save()

for x in test():
    pass