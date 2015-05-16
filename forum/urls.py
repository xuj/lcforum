# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.views.generic import ListView, DetailView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps import GenericSitemap
from django.contrib.sitemaps.views import sitemap

from . import models
from . import views
from . import rss

sitemap_thread_by_admin = {
    'queryset': models.Post.objects.filter(bygod=True),
    'date_field': 'last_edited'
}

sitemap_threads = {
    'queryset': models.Post.objects.filter(bygod=False),
    'date_field': 'last_edited'
}

sitemaps = {
    'thread_by_admin': GenericSitemap(sitemap_thread_by_admin, priority=0.7),
    'threads': GenericSitemap(sitemap_threads, priority=0.5),
}

urlpatterns = [
    # 网站首页
    url(r'^$', views.IndexView.as_view(), name='index'),
    # 论坛首页
    url(r'^forum/$', ListView.as_view(
        model=models.Post,
        template_name='forum/post/list.html',
        paginate_by=25,
        page_kwarg='p'
    ), name='forum-index'),
    # 帖子相关页面
    url(r'^forum/thread/(?P<pk>\d+)/$', views.ThreadDetail.as_view(), name='post-detail'),
    url(r'^forum/thread/(?P<pk>\d+)/reply/$', views.ReplyToPost.as_view(), name='post-reply'),
    url(r'^forum/thread/(?P<pk>\d+)/reply/(?P<reply_pk>\d+)/$', views.ReplyToPost.as_view(), name='post-reply-cited'),
    # 节点相关页面
    url(r'^forum/node/$', ListView.as_view(
        model=models.NodeTag,
        template_name='forum/nodetag/list.html'
    ), name='nodetag-list'),
    url(r'^forum/node/(?P<slug>\w+)/$', views.NodetagDetail.as_view(), name='nodetag-detail'),
    url(r'^forum/node/(?P<slug>\w+)/post/$', views.CreatePost.as_view(), name='nodetag-post'),
    # 用户操作相关页面
    url(r'^auth/reg/$', views.RegView.as_view(), name='user-reg'),
    url(r'^auth/login/$', 'django.contrib.auth.views.login', {
        'template_name': 'forum/auth/login.html'
    }, name='user-login'),
    url(r'^auth/logout/$', 'django.contrib.auth.views.logout_then_login', name='user-logout'),
    # 附件相关页面
    url(r'^upload/$', views.UploadView.as_view(), name='upload-view'),
    url(r'^attachment/(?P<pk>\d+)/', DetailView.as_view(
        model=models.Attachment,
        template_name='forum/attachment.html'
    ), name='attachment-detail'),
    url(r'^attachments/$', ListView.as_view(
        model=models.Attachment,
        template_name='forum/attachments.html',
        paginate_by=15,
        page_kwarg='p'
    ), name='attachment-list'),
    # 其它
    url(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    url(r'(?i)^rss/$', rss.PostsByAdminFeed(), name='rss'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)