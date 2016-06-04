import json,logging,inspect,functools

class Page(object):
	def __init__(self,item_count,page_index=1,page_size=10):
		self.item_count = item_count #文章总数
		self.page_size =page_size #每页显示文章数 默认为 10.
		self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)#页数 如果 总数除以每页显示文章 余数大于0 则 页数+1.
		if(item_count == 0) or (page_index>self.page_count):
			self.offset=0 #当前页面索引之前(已显示)的文章数
			self.limit=0#单页文章显示最大数
			self.page_index=1#页数
		else:
			self.page_index=page_index
			self.offset=self.page_size*(page_index-1)
			self.limit = self.page_size
			self.has_next=self.page_index<self.page_count#判断是否有下一页
			self.has_previous=self.page_index>1#判断是否有上一页
		#重组页面信息为字符串
		def __str__(self):
			return 'item_count:%s,page_count:%s,page_index:%s,page_size:%s,offset:%s,limit:%s' % (self.item_count,self.page_count,self.page_index,self.page_size,self.offset,self.limit)

		__repr__=__str__

class APIError(Exception):
	def __init__(self,error,data='',message=''):
		super(APIError,self).__init__(message)
		self.error = error
		self.data = data
		self.message = message

class APIValueError(APIError):
	"""docstring for APIValueError"""
	def __init__(self, field,message=''):
		super(APIValueError, self).__init__('value:invalid', field,message)

class APIresourceNotFundError(APIError):
	def __init__(self,field,message=''):
		super(APIresourceNotFundError,self).__init__('value:notfound',field,message)

class APIPermissionError(APIError):
	"""docstring for APIPermissionError"""
	def __init__(self, message=''):
		super(APIPermissionError, self).__init__('permission:forbidden','permission',message)
		
		