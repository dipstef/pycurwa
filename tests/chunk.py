import json
from pycurwa.download.chunks.chunk import Chunk
from pycurwa.download.chunks.chunks import DownloadChunks

chunk0 = Chunk(1, 3, './test.zip.chunk0', (0, 127))
chunk1 = Chunk(2, 3, './test.zip.chunk1', (128, 255))
chunk2 = Chunk(3, 3, './test.zip.chunk2', (256, 344))

print chunk0.size
print chunk1.size
print chunk2.size

print json.dumps(chunk0)
print json.dumps(chunk1)
print json.dumps(chunk2)

downloads = DownloadChunks('http://test.com/test.zip', './test.zip', 345, [chunk0, chunk1, chunk2])

#print downloads
assert downloads.is_completed()

downloads.save()