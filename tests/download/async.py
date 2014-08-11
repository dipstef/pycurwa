import os
from procol.console import print_err, print_line

from pycurwa.bucket import Bucket
from pycurwa.async.download import AsyncDownloads


def _completed(download):
    print_line(download.url, download.stats)


def _failed(download, error):
    print_err(download.path, error)


def _request(downloads, url, chunks=1):
    file_name = os.path.basename(url)

    request = downloads.get(url, file_name, chunks=chunks, resume=True, on_completion=_completed, on_err=_failed)

    return request


def main():

    bucket = Bucket()
    bucket.max_speed = 200 * 1024

    bucket = None

    downloads = AsyncDownloads(bucket=bucket, max_connections=11)

    _request(downloads, 'http://download.thinkbroadband.com/10MB.zip', chunks=4)
    _request(downloads, 'http://download.thinkbroadband.com/5MB.zip', chunks=4)


if __name__ == "__main__":
    main()