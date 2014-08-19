from pycurwa.download import HttpDownload


def main():
    url = 'http://download.thinkbroadband.com/10MB.zip'
    url = 'http://download.thinkbroadband.com/5MB.zip'

    download_client = HttpDownload()

    stats = download_client.get(url, chunks=4, resume=True)

    print stats.speed

if __name__ == "__main__":
    main()