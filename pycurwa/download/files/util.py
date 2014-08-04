import os
import sys
from urllib import urlencode
from unicoder import byte_string, to_unicode


if sys.getfilesystemencoding().startswith('ANSI'):
    def fs_encode(string):
        return byte_string(string, encoding='utf-8')
else:
    fs_encode = lambda x: x  # do nothing


def save_join(*args):
    return fs_encode(os.path.join(*[to_unicode(x, encoding='utf-8') for x in args]))
