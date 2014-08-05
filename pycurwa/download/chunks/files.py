import os

from ..files.download import ExistingDownload, NewChunks
from ..request import DownloadHeadersRequest
from ..files.util import save_join


def get_chunks_file(request, resume=True, cookies=None, use_disposition=False):
    headers = None
    file_path = request.path

    if use_disposition:
        headers = _resolve_headers(request.url, cookies)

        if headers.disposition_name:
            directory_path = os.path.dirname(file_path) if os.path.isdir(file_path) else file_path
            file_path = save_join(directory_path, headers.disposition_name)
    try:
        chunks = ExistingDownload(request.url, file_path, resume=resume)
    except IOError:
        if headers is None:
            headers = _resolve_headers(request.url, cookies=cookies)
        chunks = NewChunks(request.url, file_path, headers.size, request.chunks)

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