# -*- coding:utf-8 -*-

from django.contrib.syndication.views import Feed
from .models import Post

class PostsByAdminFeed(Feed):
    title = u"Lcf的个人网站最新内容"
    link = "/rss/"
    description = u"Lcf的个人网站上发布的最新内容。"

    def items(self):
        return Post.objects.filter(bygod=1)[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.content_md
