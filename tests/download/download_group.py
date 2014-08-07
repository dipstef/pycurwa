from pycurwa.bucket import Bucket
from pycurwa.multi.download.group import DownloadGroup, GroupRequests


def main():
    import os

    path = os.path.dirname(__file__)

    bucket = Bucket()
    bucket.max_speed = 200 * 1024

    bucket = None

    #requests = HttpDownloadRequests(bucket=bucket)

    with DownloadGroup() as group:
        requests = GroupRequests(group, bucket=bucket)

        requests.get('http://download.thinkbroadband.com/5MB.zip', path=path, chunks=4, resume=True)
        requests.get('http://download.thinkbroadband.com/10MB.zip', path=path, chunks=4, resume=True)

        for status in group:
            for download in status.completed:
                print download.request, download.stats.speed

if __name__ == "__main__":
    main()