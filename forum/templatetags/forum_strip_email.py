# -*- coding: utf-8 -*-

from django import template

register = template.Library()


@register.filter(name='strip_email_at')
def string_email_at(value, arg='[at]'):
    return value.replace('@', arg)