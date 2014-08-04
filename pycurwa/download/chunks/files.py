import os

from httpy import HttpRequest

from ..files.download import ExistingDownload, NewChunks
from ..request import DownloadHeadersRequest
from ..files.util import save_join


def get_chunks_file(url, file_path, chunks_number=1, resume=True, cookies=None, use_disposition=False):
    headers = None
    if use_disposition:
        headers = _resolve_headers(url, cookies)

        if headers.disposition_name:
            directory_path = os.path.dirname(file_path) if os.path.isdir(file_path) else file_path
            file_path = save_join(directory_path, headers.disposition_name)
    try:
        chunks = ExistingDownload(url, file_path, resume=resume)
    except IOError:
        if headers is None:
            headers = _resolve_headers(url, cookies=cookies)
        chunks = NewChunks(url, file_path, headers.size, chunks_number)

    return chunks


def _resolve_size(url, cookies=None):
    headers = _resolve_headers(url, cookies)

    return headers.size


def _resolve_headers(url, cookies=None):
    initial = DownloadHeadersRequest(url, cookies=cookies)
    try:
        return initial.head()
    finally:
        initial.close()