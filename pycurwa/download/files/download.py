import codecs
import json
from httpy.http.headers.content import content_length
from . import DownloadChunkFiles, chunks_file_path
from .chunk import ChunkFile


class ExistingDownload(DownloadChunkFiles):

    def __init__(self, request):
        json_dict = _load_json(request.path)

        assert request.url == json_dict['url']

        chunks = _chunks(json_dict['chunks'], json_dict['number'], request.resume)

        super(ExistingDownload, self).__init__(request, request.path, json_dict['size'], chunks, request.resume)


def _load_json(file_path):
    chunks_file = chunks_file_path(file_path)

    with codecs.open(chunks_file, 'r', 'utf-8') as fh:
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


def get_chunks_file(request, response_headers):
    try:
        chunks = ExistingDownload(request)
    except IOError:
        chunks = NewDownload(request, content_length(response_headers), request.chunks, resume=request.resume)
    return chunks