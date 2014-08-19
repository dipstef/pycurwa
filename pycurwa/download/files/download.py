import codecs
import json
import os
from httpy.error import HttpError
from httpy.http.headers.content import content_length
from . import DownloadChunkFiles, chunks_file_path
from .chunk import ChunkFile


class ExistingDownload(DownloadChunkFiles):

    def __init__(self, request, json_dict):
        assert request.url == json_dict['url']

        chunks = _chunks(json_dict['chunks'], json_dict['number'], request.resume)

        super(ExistingDownload, self).__init__(request, request.path, json_dict['size'], chunks, request.resume)


def _load_json(file_path):
    with codecs.open(file_path, 'r', 'utf-8') as fh:
        json_dict = json.load(fh)

    return json_dict


def _chunks(chunks, total, resume):
    return [ChunkFile(chunk['number'], total, chunk['path'], chunk['range'], resume) for chunk in chunks]


class NewDownload(DownloadChunkFiles):

    def __init__(self, request, download_size, chunks, resume):
        super(NewDownload, self).__init__(request, request.path, download_size, chunks=[], resume=resume)
        self._create_chunks(chunks)
        self.save()

    def _create_chunks(self, chunks_number):
        chunk_size = self.size / chunks_number
        total = chunks_number - 1

        current = 0
        for number in range(chunks_number):
            end = self.size - 1 if number == total else current + chunk_size

            path = '%s.chunk%s' % (self.file_path, number)
            self._chunks.append(ChunkFile(number+1, chunks_number, path, (current, end)))

            current += chunk_size + 1


class OneChunk(NewDownload):
    def __init__(self, request, expected_size, resume=False):
        super(OneChunk, self).__init__(request, expected_size, chunks=1, resume=resume)


def get_chunks_file(request, chunks_number, response_headers):
    try:
        chunks = _load_existing(chunks_file_path(request.path), request)

        if not chunks:
            chunks = NewDownload(request, content_length(response_headers), chunks_number, resume=request.resume)
    except Exception, e:
        raise ChunkCreationError(request, request.path, e)

    return chunks


def _load_existing(chunk_file_path, request):
    if os.path.exists(chunk_file_path):
        try:
            return ExistingDownload(request, _load_json(chunk_file_path))
        except:
            os.remove(chunk_file_path)


class ChunkCreationError(HttpError):
    def __init__(self, request, *args, **kwargs):
        super(ChunkCreationError, self).__init__(request, *args, **kwargs)