from procol.console import print_err, print_line

from pycurwa.async.download import AsyncDownloads


def _completed(download):
    print_line(download.url, download.stats)


def _failed(download, error):
    print_err(download.path, error)


def _request(downloads, url, chunks=1):
    #file_name = os.path.basename(url)

    request = downloads.get(url, chunks=chunks, resume=True, on_completion=_completed, on_err=_failed)

    return request


def main():

    with AsyncDownloads(max_connections=11) as downloads:
        #_request(downloads, 'http://download.thinkbroadband.com/not_found.zip', chunks=4)
        #_request(downloads, 'http://download.thinkbroadband.com/10MB.zip', chunks=4)
        _request(downloads, 'http://download.thinkbroadband.com/5MB.zip', chunks=4)

if __name__ == "__main__":
    main()