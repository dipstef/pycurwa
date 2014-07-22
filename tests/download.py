from pycurwa.download import HTTPDownload
from pycurwa.requests import Bucket


def main():
    import os
    # url = "http://speedtest.netcologne.de/test_100mb.bin"
    url = "http://download.thinkbroadband.com/10MB.zip"
    file_name = os.path.basename(url)

    bucket = Bucket()
    bucket.set_max_speed(200 * 1024)
    #bucket = None
    print "starting"
    d = HTTPDownload(url, file_name, bucket=bucket)
    stats = d.download(chunks=20, resume=True)
    print stats.speed


if __name__ == "__main__":
    main()