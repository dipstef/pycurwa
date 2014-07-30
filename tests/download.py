from pycurwa.bucket import Bucket
from pycurwa.download.multi import MultiDownloads


def main():
    import os
    url = 'http://download.thinkbroadband.com/10MB.zip'
    file_name = os.path.basename(url)

    bucket = Bucket()
    bucket.set_max_speed(200 * 1024)

    bucket = None

    print 'starting'
    #d = HttpDownload(bucket=bucket)
    d = MultiDownloads(bucket)

    try:
        stats = d.download(url, file_name, chunks_number=20, resume=True)

        print stats.speed
    finally:
        d.close()

if __name__ == "__main__":
    main()