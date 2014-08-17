from pycurwa.download import HttpDownload


def main():
    import os
    url = 'http://download.thinkbroadband.com/10MB.zip'
    url = 'http://download.thinkbroadband.com/5MB.zip'

    #path = os.path.basename(url)
    path = os.path.dirname(__file__)

    download_client = HttpDownload()

    stats = download_client.get(url, path=path, chunks=4, resume=True)

    print stats.speed

if __name__ == "__main__":
    main()