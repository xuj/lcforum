# -*- coding: utf-8 -*-

from django import template
from ..utility import get_screen_width

register = template.Library()


@register.filter(name='truncate_by_width')
def truncate_by_width(value, max_width):
    return get_screen_width(value, max_width)