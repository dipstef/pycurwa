from pycurwa.bucket import Bucket
from pycurwa.download import HttpDownload


def main():
    url = 'http://download.thinkbroadband.com/5MB.zip'

    bucket = Bucket()
    bucket.max_speed = 200 * 1024

    bucket = None

    download_client = HttpDownload(bucket=bucket)

    stats = download_client.get(url, chunks=20, resume=True)

    print stats.speed

if __name__ == "__main__":
    main()