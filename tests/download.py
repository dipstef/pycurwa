from pycurwa.bucket import Bucket
from pycurwa.download import HttpDownload


def main():
    import os
    url = 'http://download.thinkbroadband.com/10MB.zip'
    url = 'http://download.thinkbroadband.com/5MB.zip'
    file_name = os.path.basename(url)

    bucket = Bucket()
    bucket.set_max_speed(200 * 1024)

    bucket = None

    print 'starting'
    d = HttpDownload(bucket=bucket)

    stats = d.download(url, file_name, chunks_number=1, resume=True)

    print stats.speed

if __name__ == "__main__":
    main()