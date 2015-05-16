# -*- coding: utf-8 -*-
import datetime


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip


def get_file_path(instance, filename):
    # ext = filename.split('.')[-1]
    date = datetime.date.today().isoformat().split('-')
    filename = u"{1}/{2}/{3}/{0}".format(filename, *date)
    return filename

WIDTHS = [
    (126,    1), (159,    0), (687,     1), (710,   0), (711,   1),
    (727,    0), (733,    1), (879,     0), (1154,  1), (1161,  0),
    (4347,   1), (4447,   2), (7467,    1), (7521,  0), (8369,  1),
    (8426,   0), (9000,   1), (9002,    2), (11021, 1), (12350, 2),
    (12351,  1), (12438,  2), (12442,   0), (19893, 2), (19967, 1),
    (55203,  2), (63743,  1), (64106,   2), (65039, 1), (65059, 0),
    (65131,  2), (65279,  1), (65376,   2), (65500, 1), (65510, 2),
    (120831, 1), (262141, 2), (1114109, 1),
]

def get_screen_width(input_str, max_width=None, tail='.', tail_length=3):
    """
    获取输入字符串input_str在屏幕上的显示宽度，全角字符宽度计算为2，半角字符宽度计算为1
    注意这个宽度并不能保证字符串能在屏幕上完美对齐，因为字体的原因，全角字符的宽度并不一定是半角字符的2倍
    如果仅需要获取字符串的宽度，只需提供input_str参数即可
    如果需要截取字符串，需提供最大截取宽度和省略替代符号(可选)及其最大个数(可选)
    例如，最大截取宽度(max_width)为3,输入的字符串为 u"测试字符串"(长度为10)
    那截取结果是:
    u"..."
    如果截取宽度为4，那结果是:
    u"测.."(会自动少用一个表示省略的字符)
    如果截取宽度为5，那结果是:
    u"测..."
    """

    def get_char_width(char):
        """
        查表(WIDTHS)获取单个字符的宽度
        """
        char = ord(char)
        if char == 0xe or char == 0xf:
            return 0

        for num, wid in WIDTHS:
            if char <= num:
                return wid

        return 1

    if max_width and max_width > tail_length*get_char_width(tail):
        # 最大宽度应该至少和表示省略的字符串一样长
        # str_max_width和max_width的区别在于：
        # max_width表示的是返回结果的最大宽度，包括了最后表示省略的点
        # str_max_width表示的是除去表示省略的符号后在输入字符串中截取部分的最大长度
        str_max_width = max_width - tail_length*get_char_width(tail)
    elif max_width and max_width == tail_length*get_char_width(tail):
        # 如果最大宽度刚好和表示省略的字符串宽度一样，那就直接返回表示省略的字符串
        return tail*tail_length
    elif max_width:
        # 如果出现提供了最大宽度但最大宽度还不如结尾表示省略的字符宽度大的时候就抛出异常
        raise AttributeError

    total_width = 0
    result = input_str

    for i in range(0, len(input_str)):
        total_width += get_char_width(input_str[i])

        if not max_width:
            continue

        # 当接近str_max_width时有几种情况：
        # 一种最离str_max_width还有一个半角字符，这种情况就继续循环
        # 另一种是截完当前字符总长度刚好为str_max_width，这种情况就值止分析下面的字符，
        # 直接在当前字符后面加上表示省略的符号后返回，这时总的长度刚好为max_width
        # 最后一种情况是截取完上一个字符后总宽度刚好和str_max_width差一个半角字符，
        # 刚好当前读取的字符的宽度是2（全角字符），那从输入字符串中截取的长度不可能和
        # str_max_width完全相同，会比str_max_width大一个半角宽度，这种情况就把表示
        # 省略的字符少显示一个，加到结尾，这样最后返回值的长度刚好也是max_width.
        if total_width < str_max_width:
            continue
        elif total_width == str_max_width:
            result = input_str[0:i+1] + tail*tail_length
            break
        else:
            result = input_str[0:i+1] + tail*(tail_length-1)
            break

    return result if max_width else total_width