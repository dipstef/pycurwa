import os

from ..files.download import ExistingDownload, NewDownload
from ..request import DownloadHeadersRequest
from ..files.util import save_join


def get_chunks_file(request, cookies=None):
    headers = None

    if os.path.isdir(request.path):
        headers = _resolve_headers(request.url, cookies)

        file_name = headers.file_name or os.path.basename(request.url)

        assert file_name
        request.path = save_join(request.path, file_name)

    chunks = _download_chunks(request, cookies, headers)

    return chunks


def _download_chunks(request, cookies=None, headers=None):
    try:
        chunks = ExistingDownload(request)
    except IOError:
        headers = headers or _resolve_headers(request.url, cookies=cookies)
        chunks = NewDownload(request, headers.size, request.chunks, resume=request.resume)
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