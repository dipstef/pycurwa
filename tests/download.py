from pycurwa.bucket import Bucket
from pycurwa.download import HttpDownload


def main():
    import os
    url = 'http://download.thinkbroadband.com/10MB.zip'
    url = 'http://download.thinkbroadband.com/5MB.zip'
    file_name = os.path.basename(url)

    bucket = Bucket()
    bucket.max_speed = 200 * 1024

    bucket = None

    print 'starting'
    d = HttpDownload(bucket=bucket)

    stats = d.get(url, path=file_name, chunks=1, resume=True)

    print stats.speed

if __name__ == "__main__":
    main()