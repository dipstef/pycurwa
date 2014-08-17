import os
from httpy.error import HttpNotFound

from procol.console import print_err, print_line

from pycurwa.async.download import AsyncDownloads, AsyncDownloadFutures


def _completed(download):
    print_line(download.url, download.stats)


def _failed(download, error):
    print_err(download.path, error)


def _request(downloads, url, chunks=1):
    file_name = os.path.basename(url)

    request = downloads.get(url, file_name, chunks=chunks, resume=True, on_completion=_completed, on_err=_failed)

    return request


def main():
    with AsyncDownloads() as downloads:
        downloads.head('http://download.thinkbroadband.com/not_found.zip', on_err=print_err)
        _request(downloads, 'http://download.thinkbroadband.com/not_found.zip', chunks=4)

    with AsyncDownloadFutures() as downloads:
        try:
            response = downloads.head('http://download.thinkbroadband.com/not_found.zip')
            assert not response.status
        except HttpNotFound, e:
            print_err(e)

        try:
            download = downloads.get('http://download.thinkbroadband.com/not_found.zip', chunks=4)
            download.perform()
        except HttpNotFound, e:
            print_err(e)


if __name__ == "__main__":
    main()