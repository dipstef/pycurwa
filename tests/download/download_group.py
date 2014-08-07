from pycurwa.bucket import Bucket
from pycurwa.download import  HttpDownloadRequests
from pycurwa.multi.download.group import DownloadGroup


def main():
    import os

    path = os.path.dirname(__file__)

    bucket = Bucket()
    bucket.max_speed = 200 * 1024

    bucket = None

    requests = HttpDownloadRequests(bucket=bucket)

    with DownloadGroup() as group:
        group.add(requests.get('http://download.thinkbroadband.com/5MB.zip', path=path, chunks=4, resume=True))
        #group.add(requests.get('http://download.thinkbroadband.com/10MB.zip', path=path, chunks=4, resume=True))

        group.perform()

if __name__ == "__main__":
    main()