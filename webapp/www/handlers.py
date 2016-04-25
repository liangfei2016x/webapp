import re,time,json,logging,hashlib,base64,asyncio

from webapp.www.coroweb import get,post
from webapp.www.models import User,Comment,Blog,next_id

@get('/')
@asyncio.coroutine
def index(request):
	print('OKOKOK')
	users = yield from User.findAll()
	print(users)
	return {
		'__template__':'test.html',
		'users':users
	}