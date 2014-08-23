import codecs
import os
import sys
import fcntl

from unicoder import byte_string, to_unicode


if sys.getfilesystemencoding().startswith('ANSI'):
    def fs_encode(string):
        return byte_string(string, encoding='utf-8')
else:
    fs_encode = lambda x: x  # do nothing


def join_encoded(*args):
    return fs_encode(os.path.join(*[to_unicode(x, encoding='utf-8') for x in args]))


def open_locked(path, mode='r', encoding=None, blocking=True, **kwargs):
    open_fun = codecs.open if encoding else open
    if encoding:
        kwargs['encoding'] = encoding

    fp = open_fun(path, mode, **kwargs)
    if blocking:
        fcntl.flock(fp, fcntl.LOCK_EX)
    else:
        try:
            fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError, e:
            raise FileLocked(path, e)

    return fp


class FileLocked(IOError):
    def __init__(self, path, io_error):
        super(FileLocked, self).__init__(path, *io_error.args)
        self.path = path