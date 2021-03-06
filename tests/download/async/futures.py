import os

from pycurwa.async.download import AsyncDownloadFutures


def _request(downloads, url, chunks=1):
    file_name = os.path.basename(url)

    request = downloads.get(url, path=file_name, chunks=chunks, resume=True)

    return request


def main():

    downloads = AsyncDownloadFutures(max_connections=10)

    try:
        #request1 = _request(downloads, 'http://download.thinkbroadband.com/10MB.zip')
        request2 = _request(downloads, 'http://download.thinkbroadband.com/5MB.zip', chunks=20)

        #stats1 = request1.perform()
        #print stats1.speed

        stats2 = request2.perform()
        print stats2.speed

    finally:
        downloads.close()

if __name__ == "__main__":
    main()