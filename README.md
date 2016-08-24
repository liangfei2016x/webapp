# webapp
个人博客管理系统

编辑器：PyCharm 或 sublime Text


运用技术：Python 3.5 + mysql（数据库）+uikit框架（web框架、主要用了CSS样式）+Vue.js(数据驱动的组件).

项目描述：

        采用MVC模式实现简单的个人博客管理系统，主要包括：
        用户模块：实现了用户注册登录注销浏览等功能
        管理模块：实现了创建、修改、删除博客，获取用户和用户评论列表
        API模块：获取博客，用户的相关信息以JSON字符串返回
项目详情：
      
        用户浏览页面包括：

        注册页：GET /register

        登录页：GET /signin

        注销页：GET /signout

        首页：GET /

        日志详情页：GET /blog/:blog_id

        管理页面包括：

        评论列表页：GET /manage/comments

        日志列表页：GET /manage/blogs

        创建日志页：GET /manage/blogs/create

        修改日志页：GET /manage/blogs/

        用户列表页：GET /manage/users
        
        获取日志：GET /api/blogs

        后端API包括：

        获取日志：GET /api/blogs

        创建日志：POST /api/blogs

        修改日志：POST /api/blogs/:blog_id

        删除日志：POST /api/blogs/:blog_id/delete

        获取评论：GET /api/comments

        创建评论：POST /api/blogs/:blog_id/comments

        删除评论：POST /api/comments/:comment_id/delete

        创建新用户：POST /api/users

        获取用户：GET /api/users
