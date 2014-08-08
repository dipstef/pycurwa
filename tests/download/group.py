from procol.console import print_err

from pycurwa.bucket import Bucket
from pycurwa.multi.download import MultiDownloadsRequests


def main():
    import os

    path = os.path.dirname(__file__)

    bucket = Bucket()
    bucket.max_speed = 200 * 1024

    bucket = None

    with MultiDownloadsRequests(max_connections=10) as requests:
        requests = requests.create_group()

        requests.get('http://download.thinkbroadband.com/5MB.zip', path=path, chunks=4, resume=True)
        #requests.get('http://download.thinkbroadband.com/10MB.zip', path=path, chunks=20, resume=True)

        group = requests.submit()

        for status in group.iterate_finished():
            for download in status.completed:
                print download.stats
            for download in status.failed:
                print_err(download.stats)

if __name__ == "__main__":
    main()