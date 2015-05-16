# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView, FormView, TemplateView
from django.contrib.auth import authenticate, login
from django.forms.models import modelform_factory
from django.forms.widgets import PasswordInput
from django.utils.six import BytesIO

from .models import *
from .utility import get_client_ip


class IndexView(TemplateView):
    template_name = 'forum/index.html'

    def get_context_data(self, **kwargs):
        posts = Post.objects.all()
        replies = Reply.objects.all()
        # 这里和下面的headline那里加的这个判断是为了空数据库的时候出现IndexError
        admin_post = posts.filter(bygod=1) or [None, ]
        return {
            'post_latest': posts[:10],
            'reply_latest': replies[:10],
            'admin_post_latest': admin_post[1:7],
            'admin_reply_latest': replies.filter(bygod=1)[:5],
            'headline': admin_post[0] or []
        }


class NodetagDetail(ListView):
    model = Post
    template_name = 'forum/nodetag/detail.html'
    paginate_by = 25
    page_kwarg = 'p'

    def get_queryset(self):
        node = get_object_or_404(NodeTag, slug=self.kwargs['slug'])
        all_posts = super(NodetagDetail, self).get_queryset()
        posts_belong_to_this_node = all_posts.filter(node=node)
        return posts_belong_to_this_node

    def get_context_data(self, **kwargs):
        context = super(NodetagDetail, self).get_context_data(**kwargs)
        context['nodetag'] = get_object_or_404(NodeTag, slug=self.kwargs['slug'])
        return context


class ThreadDetail(ListView):
    model = Reply
    template_name = 'forum/post/detail.html'
    paginate_by = 20
    page_kwarg = 'p'

    def get_queryset(self):
        all_replies = super(ThreadDetail, self).get_queryset()
        replies_belong_to_this_post = all_replies.filter(post_node=self.kwargs['pk']).order_by('pk')
        return replies_belong_to_this_post

    def get_context_data(self, **kwargs):
        context = super(ThreadDetail, self).get_context_data(**kwargs)
        context['post'] = get_object_or_404(Post, pk=self.kwargs['pk'])
        return context


class ReplyToPost(CreateView):
    model = Reply
    fields = ['content', 'guest_name', 'guest_email', 'need_notification']
    template_name = 'forum/reply.html'
    post_node = None
    cited_reply = None

    def get_initial(self):
        if 'reply_pk' in self.kwargs.keys():
            cited_reply = self.get_cited_reply()
            cited_author = getattr(cited_reply.author, 'username', None) or cited_reply.guest_name
            raw_content = BytesIO(getattr(cited_reply, 'content', ''))

            line_no = 0
            # There is a bug here:
            # code block wrapped with "```" will not be rendered properly in quote-block.
            initial_content = u'\r\n> **以下内容引用自{0}发表的回复：**\r\n> \r\n'.format(cited_author)

            for line in raw_content:
                if line_no >= 13:
                    initial_content += u'> \r\n> ...*(以下内容在引用时被省略)*'
                    break

                line = u'> ' + line
                initial_content += line
                line_no += 1

            return {
                'content': initial_content,
            }
        else:
            return super(ReplyToPost, self).get_initial()

    def form_valid(self, form):
        # http://www.wenda.io/questions/4377698/pass-current-user-to-initial-for-createview-in-django.html
        form.instance.author = self.request.user if self.request.user.is_authenticated() else None
        form.instance.post_node = self.get_post_node()
        form.instance.title = 'Re:' + self.get_post_node().title
        form.instance.ip_addr = get_client_ip(self.request)
        form.instance.reply_to = self.get_cited_reply() if 'reply_pk' in self.kwargs else None

        return super(ReplyToPost, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ReplyToPost, self).get_context_data(**kwargs)
        context['post_node'] = self.get_post_node()
        return context

    def get_form_class(self):
        if self.request.user.is_superuser:
            self.fields = ['content', 'bygod', 'need_notification']
        elif self.request.user.is_authenticated():
            self.fields = ['content', 'need_notification']

        return super(ReplyToPost, self).get_form_class()

    def get_post_node(self):
        return self.post_node or get_object_or_404(Post, pk=self.kwargs['pk'])

    def get_cited_reply(self):
        return self.cited_reply or get_object_or_404(Reply, pk=self.kwargs['reply_pk'])


class CreatePost(CreateView):
    model = Post
    fields = ['title', 'content', 'guest_name', 'guest_email', 'need_notification']
    template_name = 'forum/post.html'
    node = None  # node可能可以用@property解决

    def form_valid(self, form):
        form.instance.author = self.request.user if self.request.user.is_authenticated() else None
        form.instance.node = self.get_node()
        form.instance.ip_addr = get_client_ip(self.request)
        return super(CreatePost, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(CreatePost, self).get_context_data(**kwargs)
        context['node'] = self.get_node()
        return context

    def get_form_class(self):
        if self.request.user.is_superuser:
            # 一开始我这里用的是self.fields.remove('bygod')
            # 但是只能生效一次，然后就会出现异常提示说要REMOVE的ITEM不存在
            # 为什么呢？
            # >>> class Test(object):
            # ...     i = [1, 2, 3]
            # >>> id(Test.i)
            # 41923368
            # >>> t = Test()
            # >>> id(t.i)
            # 41923368
            # 我想以上就是答案了 :)

            # 如果从登陆状态变为游客的状态，并不需要重新把fields设置成初始状态
            # 因为这里对fields的更改只不过是对某个实例的fields进行了更改
            # 并没有改变类中的属性
            self.fields = ['title', 'content', 'need_notification', 'bygod']
        elif self.request.user.is_authenticated():
            self.fields = ['title', 'content', 'need_notification']

        return super(CreatePost, self).get_form_class()

    def get_node(self):
        return self.node or get_object_or_404(NodeTag, slug=self.kwargs['slug'])


class RegView(FormView):
    template_name = 'forum/auth/reg.html'

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        username = request.POST['username']
        email = request.POST.get('email', None)
        password = request.POST['password']

        if form.is_valid():
            User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            self.object = authenticate(
                username=username,
                password=password
            )
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        # See this: http://stackoverflow.com/a/9899170
        return self.kwargs.get('next', '/')

    def form_valid(self, form):
        # See this: http://stackoverflow.com/a/6039782
        login(self.request, self.object)
        return HttpResponseRedirect(self.get_success_url())

    def get_form_class(self):
        return modelform_factory(
            User,
            fields=['username', 'email', 'password'],
            widgets={
                'password': PasswordInput()
            },
            labels={
                'email': u"电子邮箱"
            }
        )


class UploadView(CreateView):
    template_name = 'forum/upload.html'
    fields = ['attachment', 'remark']
    model = Attachment

    def form_valid(self, form):
        form.instance.user = self.request.user if self.request.user.is_authenticated() else None
        return super(UploadView, self).form_valid(form)

    def get_success_url(self):
        # See this: http://stackoverflow.com/a/9899170
        return self.kwargs.get('next', '/')
