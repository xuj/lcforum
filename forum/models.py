# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.db import models
from django.core.urlresolvers import reverse
from django.core import validators
from django.conf import settings
from django.core.mail import send_mass_mail
from django.contrib.sitemaps import ping_google
import markdown
from .utility import get_file_path
from PIL import Image
import os.path
import datetime


# 一般来说，默认只有主键被索引了（db_index = True）
# 增加索引一般只有对数据比较多的时候才有意义，而且增加了主键后每次增删改都会重建索引
class DateTimeBase(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_edited = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PostBase(DateTimeBase):
    title = models.CharField(max_length=200, error_messages={
        'blank': "标题不能为空",
        'null': "标题不能为空",
        'invalid': "您输入了一个无效的标题，标题的长度请控制在100个字符内"
    }, help_text="☞标题为必填且不能超过100个字符", verbose_name=u"标题")
    content = models.TextField(blank=True, null=True,
                               help_text="☞支持Markdown语法. 内容可以留空，但不要输入无意义的内容",
                               verbose_name="内容")
    author = models.ForeignKey(User, blank=True, null=True, related_name='%(class)s', on_delete=models.SET_NULL)
    content_md = models.TextField(blank=True, null=True)
    bygod = models.BooleanField(blank=True, default=False,
                                help_text="☞将这篇文章归入管理员文集",
                                verbose_name="归档")
    guest_name = models.CharField(max_length=30, default="Guest", verbose_name="游客称呼", blank=True, null=True,
                                  validators=[
                                      validators.RegexValidator(r'^[\w.@+-]+$', "名字中包含不允许的字符.", 'invalid')
                                  ])
    guest_email = models.EmailField(
        max_length=254, verbose_name="游客联系方式", blank=True, null=True,
        help_text="您的邮件地址在显示时会将@替换为[at]",
        error_messages={
            'invalid': "您输入了一个无效的邮件地址，请修改或留空"
        }
    )
    ip_addr = models.IPAddressField(default='0.0.0.0', verbose_name="IP地址", help_text="发信人的IP地址")

    need_notification = models.BooleanField(blank=True, default=True,
                                            help_text="☞被回复时用邮件通知我（需要填写有效的邮箱地址）",
                                            verbose_name="回复提醒")

    def get_author_info(self):
        if self.author:
            return self.author.username, self.author.email
        else:
            return self.guest_name, self.guest_email

    def save(self, *args, **kwargs):
        self.bygod = self.bygod if getattr(self.author, 'is_superuser', False) else False
        self.content_md = markdown.markdown(
            self.content,
            safe_mode='escape',
            output_format='html5',
            extensions=[
                'markdown.extensions.extra',
                'markdown.extensions.sane_lists',
                'markdown.extensions.codehilite(noclasses=True, linenums=False)',
                'markdown.extensions.toc'
            ]
        )
        super(PostBase, self).save(*args, **kwargs)
        # ping_google() will make posting process slow if your server cannot connect with google servers
        # ie, host in china normally cannot ping google smoothly.
        # try:
        #     ping_google()
        # except Exception:
        #     pass

    class Meta:
        abstract = True


class NodeTag(DateTimeBase):
    name = models.CharField(max_length=50, error_messages={
        'blank': "节点的名称不能为空",
        'null': "节点的名称不能为空",
        'invalid': "您输入了一个无效的节点名称，节点名称的长度不能超过50个字符"
    }, help_text="☞节点名称为必填且不能超过50个字符", verbose_name="节点名称", unique=True)
    description = models.TextField(blank=True, null=True,
                                   help_text="☞关于节点讨论主题的简要描述",
                                   verbose_name="节点描述")
    slug = models.CharField(max_length=30, help_text="☞节点的英文简写", verbose_name="节点代号", unique=True)

    def get_absolute_url(self):
        return reverse('nodetag-detail', kwargs={'slug': self.slug})

    def __unicode__(self):
        return self.name


class Post(PostBase):
    node = models.ForeignKey(NodeTag, null=True, related_name='posts', on_delete=models.SET_NULL)

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})

    def get_full_url(self):
        return getattr(settings, "ABSOLUTE_URL_PREFIX", "http://localhost") + self.get_absolute_url()

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ['-pk']


class Reply(PostBase):
    post_node = models.ForeignKey(Post, null=True, related_name='replies', on_delete=models.SET_NULL)
    reply_to = models.ForeignKey('self', null=True, related_name='replies', on_delete=models.SET_NULL)

    def get_absolute_url(self):
        if getattr(self.post_node, 'pk', None):
            return reverse('post-detail', kwargs={'pk': self.post_node.pk})

        return reverse('forum-index')

    def __unicode__(self):
        return u"#{0} reply of '{1}'".format(self.pk, getattr(self.post_node, 'title', 'A Deleted Post'))

    def save(self, *args, **kwargs):
        super(Reply, self).save(*args, **kwargs)

        notify_op = getattr(self.post_node, 'need_notification', False)
        notify_cited = getattr(self.reply_to, 'need_notification', False)

        if notify_op or notify_cited:
            mails = []
            post_url = self.post_node.get_full_url()
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "root@localhost")
            subject_default = "{0}, {1}回应了您在[lcfcn.com]的{2}"
            date_string = datetime.date.today().isoformat()
            message_default = """
{0},
{1} 回复了您在[lcfcn.com]发表的{2}.

内容如下:

{3}

原文地址是:
{4}

您在发文时同意了接收回复通知, 所以会收到这封邮件.

{5}
"""

            if notify_op:
                receiver = self.post_node.get_author_info()
                if receiver[1]: # have a valid email address
                    sender = self.get_author_info()
                    subject = subject_default.format(receiver[0], sender[0], "文章")
                    message = message_default.format(receiver[0], sender[0], "文章",
                                                     self.content, post_url,
                                                     date_string)
                    mails.append((subject, message, from_email, [self.post_node.get_author_info()[1], ]))

            if notify_cited:
                receiver = self.reply_to.get_author_info()
                print receiver
                if receiver[1]: # have a valid email address
                    sender = self.get_author_info()
                    subject = subject_default.format(receiver[0], sender[0], "评论")
                    message = message_default.format(receiver[0], sender[0], "评论",
                                                     self.content, post_url,
                                                     date_string)
                    mails.append((subject, message, from_email, [self.reply_to.get_author_info()[1], ]))

            send_mass_mail(mails)

    class Meta:
        verbose_name_plural = 'replies'
        ordering = ['-pk']


class Attachment(DateTimeBase):
    width = models.PositiveIntegerField("图片宽度", blank=True, null=True, default=0,
                                        help_text="图片的宽度，单位为像素(px)")
    height = models.PositiveIntegerField("图片长度", blank=True, null=True, default=0,
                                         help_text="图片的长度，单位为像素(px)")
    image_format = models.CharField("图片格式", max_length=100, blank=True, null=True,
                                    help_text="图片的格式")
    is_image = models.BooleanField("是否图片文件", blank=True, default=False)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    remark = models.CharField("文件备注", max_length=200, blank=True, null=True,
                              help_text=u"文件上传后会被统一命名，建议加上备注以便查找")
    attachment = models.FileField('选择文件', null=True, upload_to=get_file_path,
                                  help_text="选择要上传的文件，请不要上传非法、危险以及涉及版权问题的文件")

    def filename(self):
        return os.path.basename(self.attachment.name)

    def file_exists(self):
        return self.attachment and os.path.isfile(self.attachment.path)

    def save(self, *args, **kwargs):
        try:
            pic = Image.open(self.attachment)
            self.is_image = True
            self.image_format = pic.format
            self.width, self.height = pic.size
        except (IOError, UnicodeEncodeError):
            # Pillow will cause UnicodeEncodeError if input filename is a unicode string
            # and ONLY happens when input file is not a valid image format.
            self.is_image = False
            self.width, self.height = 0, 0
        super(Attachment, self).save(*args, **kwargs)

    def __unicode__(self):
        return "{0}({1})".format(self.filename(), self.remark)

    def get_absolute_url(self):
        return reverse('attachment-detail', kwargs={'pk': self.pk})

    class Meta:
        ordering = ['-pk']