import codecs
import json
import os
from procol.console import print_err_trace
from unicoder import to_unicode

from . import DownloadChunkFiles, chunks_file_path
from .chunk import ChunkFile
from .error import ChunksAlreadyExisting, ChunkCreationException


def load_existing_chunks(download_path, request):
    chunk_file_path = chunks_file_path(download_path)
    if os.path.exists(chunk_file_path):
        try:
            json_dict = _load_json(chunk_file_path)
            if request.url != json_dict['url']:
                raise ChunksAlreadyExisting(request, request.path, chunk_file_path, json_dict['url'])

            chunks = _chunks(json_dict['chunks'], json_dict['number'], request.resume)

            return DownloadChunkFiles(request, request.path, json_dict['size'], chunks, request.resume)
        except EnvironmentError:
            os.remove(chunk_file_path)
        except BaseException, error:
            print_err_trace('Error Loading Chunks: ', error)
            os.remove(chunk_file_path)


def _load_json(file_path):
    with codecs.open(file_path, 'r', 'utf-8') as fh:
        json_dict = json.load(fh)

    return json_dict


def _chunks(chunks, total, resume):
    return [ChunkFile(chunk['number'], total, chunk['path'], chunk['range'], resume) for chunk in chunks]


def create_chunks_file(request, chunks_number, size, resume=False):
    try:
        chunks = []
        path = to_unicode(request.path)
        for number, chunk_range in _iterate_ranges(chunks_number, size):
            path = u'%s.chunk%s' % (path, number)
            chunks.append(ChunkFile(number + 1, chunks_number, path, chunk_range))

        chunks_file = DownloadChunkFiles(request, request.path, size, chunks, resume)
        chunks_file.save()

        return chunks_file
    except BaseException, e:
        raise ChunkCreationException(request, request.path, e)


def _iterate_ranges(chunks_number, size):
    chunk_size = size / chunks_number
    total = chunks_number - 1

    current = 0
    for number in range(chunks_number):
        end = size - 1 if number == total else current + chunk_size

        yield number, (current, end)
        current += chunk_size + 1

