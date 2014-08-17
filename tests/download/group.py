from procol.console import print_err

from pycurwa.async.download import AsyncDownloadFutures


def _print_stats(group):
    for status in group.iterate_finished():
        for download in status.completed:
            print download.stats
        for download in status.failed:
            print_err(download.stats, download.error)


def main():
    import os

    path = os.path.dirname(__file__)

    requests = AsyncDownloadFutures(max_connections=10)

    try:
        with requests.group() as group:

            group.get('http://download.thinkbroadband.com/5MB.zip', path=path, chunks=4, resume=True)
            #group.get('http://download.thinkbroadband.com/10MB.zip', path=path, chunks=4, resume=True)

            _print_stats(group)

    finally:
        requests.close()

if __name__ == "__main__":
    main()