import re,time,json,logging,hashlib,base64,asynico

from coroweb import get,post
from models import User,Comment,Blog,next_id

@get('get')
asynico def index(request):
	users = await User.findAll()
	return {
		'__temple__':'test.html',
		'users':users
	}