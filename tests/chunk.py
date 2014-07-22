import json
from pycurwa.download.chunks import Chunk, DownloadChunks

chunk0 = Chunk('./test.zip.chunk0', 0, 127)
chunk1 = Chunk('./test.zip.chunk1', 128, 255)
chunk2 = Chunk('./test.zip.chunk2', 256, 344)

print json.dumps(chunk0)
print json.dumps(chunk1)
print json.dumps(chunk2)

downloads = DownloadChunks('http://test.com/test.zip', 345, './test.zip', [chunk0, chunk1, chunk2])

#print downloads
assert downloads.is_completed()

downloads.save()