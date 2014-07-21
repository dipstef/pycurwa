import codecs
import os
import re
import pycurl
import time
from request import HTTPRequestBase
from util import fs_encode


class ChunkInfo(object):
    def __init__(self, name):
        self.name = unicode(name)
        self.size = 0
        self.resume = False
        self.chunks = []

    def __repr__(self):
        ret = "ChunkInfo: %s, %s\n" % (self.name, self.size)
        for i, c in enumerate(self.chunks):
            ret += "%s# %s\n" % (i, c[1])

        return ret

    def set_size(self, size):
        self.size = int(size)

    def add_chunk(self, name, range):
        self.chunks.append((name, range))

    def clear(self):
        self.chunks = []

    def create_chunks(self, chunks):
        self.clear()
        chunk_size = self.size / chunks

        current = 0
        for i in range(chunks):
            end = self.size - 1 if (i == chunks - 1) else current + chunk_size

            self.add_chunk("%s.chunk%s" % (self.name, i), (current, end))

            current += chunk_size + 1

    def save(self):
        fs_name = fs_encode("%s.chunks" % self.name)

        with codecs.open(fs_name, "w", "utf_8") as file_header:
            file_header.write("name:%s\n" % self.name)
            file_header.write("size:%s\n" % self.size)

            for i, c in enumerate(self.chunks):
                file_header.write("#%d:\n" % i)
                file_header.write("\tname:%s\n" % c[0])
                file_header.write("\trange:%i-%i\n" % c[1])


    @staticmethod
    def load(name):
        fs_name = fs_encode("%s.chunks" % name)

        if not os.path.exists(fs_name):
            raise IOError()

        fh = codecs.open(fs_name, "r", "utf_8")

        name = fh.readline()[:-1]
        size = fh.readline()[:-1]

        if name.startswith("name:") and size.startswith("size:"):
            name = name[5:]
            size = size[5:]
        else:
            fh.close()
            raise WrongFormat()

        ci = ChunkInfo(name)
        ci.loaded = True
        ci.set_size(size)
        while True:
            if not fh.readline(): #skip line
                break
            name = fh.readline()[1:-1]
            range = fh.readline()[1:-1]

            if name.startswith("name:") and range.startswith("range:"):
                name = name[5:]
                range = range[6:].split("-")
            else:
                raise WrongFormat()

            ci.add_chunk(name, (long(range[0]), long(range[1])))

        fh.close()
        return ci

    def remove(self):
        fs_name = fs_encode("%s.chunks" % self.name)
        if os.path.exists(fs_name):
            os.remove(fs_name)

    def get_count(self):
        return len(self.chunks)

    def get_chunk_name(self, index):
        return self.chunks[index][0]

    def get_chunk_range(self, index):
        return self.chunks[index][1]


class HTTPChunk(HTTPRequestBase):
    def __init__(self, chunk_id, download, info, bytes_range):
        super(HTTPChunk, self).__init__(download.cj, options=download.options)

        self.id = chunk_id

        self._info = info
        self._download = download # HTTPDownload instance
        self._range = bytes_range # tuple (start, end)

        self._resume = info.resume
        self.log = download.log

        self.size = bytes_range[1] - bytes_range[0] if bytes_range else -1
        self.arrived = 0

        self._header_parsed = False #indicates if the header has been processed

        self.fp = None #file handle

        self._bom_checked = False # check and remove byte order mark

        self._rep = None

        self.sleep = 0.000
        self._last_size = 0

    def __repr__(self):
        return "<HTTPChunk id=%d, size=%d, arrived=%d>" % (self.id, self.size, self.arrived)

    def get_handle(self):
        """ returns a Curl handle ready to use for perform/multiperform """

        self._set_request_context(self._download.url, self._download.get, self._download.post, self._download.referrer,
                                  self._download.cj)

        self.curl.setopt(pycurl.WRITEFUNCTION, self._write_body)
        self.curl.setopt(pycurl.HEADERFUNCTION, self._write_header)

        # request all bytes, since some servers in russia seems to have a defect arihmetic unit

        fs_name = fs_encode(self._info.get_chunk_name(self.id))

        if self._resume:
            self.fp = open(fs_name, "ab")

            self.arrived = self.fp.tell()

            if not self.arrived:
                self.arrived = os.stat(fs_name).st_size

            if self._range:
                #do nothing if chunk already finished
                if self.arrived + self._range[0] >= self._range[1]: return None

                if self.id == len(self._info.chunks) - 1: #as last chunk dont set end range, so we get everything
                    range = "%i-" % (self.arrived + self._range[0])
                else:
                    range = "%i-%i" % (self.arrived + self._range[0], min(self._range[1] + 1, self._download.size - 1))

                self.log.debug("Chunked resume with range %s" % range)
                self.curl.setopt(pycurl.RANGE, range)
            else:
                self.log.debug("Resume File from %i" % self.arrived)
                self.curl.setopt(pycurl.RESUME_FROM, self.arrived)

        else:
            if self._range:
                if self.id == len(self._info.chunks) - 1: # see above
                    range = "%i-" % self._range[0]
                else:
                    range = "%i-%i" % (self._range[0], min(self._range[1] + 1, self._download.size - 1))

                self.log.debug("Chunked with range %s" % range)
                self.curl.setopt(pycurl.RANGE, range)

            self.fp = open(fs_name, "wb")

        return self.curl

    def _write_header(self, buf):
        self.header += buf

        #@TODO forward headers?, this is possibly unneeeded, when we just parse valid 200 headers
        # as first chunk, we will parse the headers
        if not self._range and self.header.endswith("\r\n\r\n"):
            self._parse_header()
        elif not self._range and buf.startswith("150") and "data connection" in buf: #ftp file size parsing
            size = re.search(r"(\d+) bytes", buf)
            if size:
                self._download.size = int(size.group(1))
                self._download.chunk_support = True

        self._header_parsed = True

    def _write_body(self, buf):
        #ignore BOM, it confuses unrar
        if not self._bom_checked:
            if [ord(b) for b in buf[:3]] == [239, 187, 191]:
                buf = buf[3:]
            self._bom_checked = True

        size = len(buf)

        self.arrived += size

        self.fp.write(buf)

        if self._download.bucket:
            self._download.bucket.sleep_above_rate(size)
        else:
            # Avoid small buffers, increasing sleep time slowly if buffer size gets smaller
            # otherwise reduce sleep time percentual (values are based on tests)
            # So in general cpu time is saved without reducing bandwith too much

            if size < self._last_size:
                self.sleep += 0.002
            else:
                self.sleep *= 0.7

            self._last_size = size

            time.sleep(self.sleep)

        if self._range and self.arrived > self.size:
            return 0

    def _parse_header(self):
        """parse data from recieved header"""
        for orgline in self.decode_response(self.header).splitlines():
            line = orgline.strip().lower()
            if line.startswith("accept-ranges") and "bytes" in line:
                self._download.chunk_support = True

            if line.startswith("content-disposition") and "filename=" in line:
                name = orgline.partition("filename=")[2]
                name = name.replace('"', "").replace("'", "").replace(";", "").strip()

                self._download.disposition_name = name
                self.log.debug("Content-Disposition: %s" % name)

            if not self._resume and line.startswith("content-length"):
                self._download.size = int(line.split(":")[1])

        self._header_parsed = True

    def stop(self):
        """The download will not proceed after next call of writeBody"""
        self._range = [0, 0]
        self.size = 0

    def reset_range(self):
        """ Reset the range, so the download will load all data available  """
        self._range = None

    def set_range(self, range):
        self._range = range
        self.size = range[1] - range[0]

    def flush_file(self):
        """  flush and close file """
        self.fp.flush()
        os.fsync(self.fp.fileno()) #make sure everything was written to disk
        self.fp.close() #needs to be closed, or merging chunks will fail

    def close(self):
        """ closes everything, unusable after this """
        if self.fp:
            self.fp.close()

        self.curl.close()


class WrongFormat(Exception):
    pass


class UnexpectedChunkContent(Exception):
    def __init__(self):
        super(UnexpectedChunkContent, self).__init__("Downloaded content was smaller than expected. "
                                                     "Try to reduce download connections.")


class FallbackToSingleConnection(Exception):
    def __init__(self, error):
        message = "Download chunks failed, fallback to single connection | %s" % (str(error))
        super(FallbackToSingleConnection, self).__init__(message)
        self.message = message