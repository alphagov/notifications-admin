from io import RawIOBase
from time import sleep
from zipfile import ZipFile


class InterruptibleRawIOWrapper(RawIOBase):
    """
    A fileobj wrapper that will make itself "interruptible" by calling sleep(0)
    every time a reading or writing operation is performed, and will *attempt*
    to reduce the size of reads performed to below the read_limit (and therefore
    increase the frequency of read calls). The latter will of course not be
    possible for e.g. .read(-1) calls which are expected to return everything
    up to EOF in all cases.

    This should allow a greenthread event loop to interrupt long processing
    operations on this file, as long as the processing code is written in a
    "memory efficient" way.
    """

    def __init__(self, wrapped, read_limit=8_192):
        self._wrapped = wrapped
        self._read_limit = read_limit

    def close(self, *args, **kwargs):
        return self._wrapped.close(*args, **kwargs)

    @property
    def closed(self):
        return self._wrapped.closed

    def fileno(self, *args, **kwargs):
        return self._wrapped.fileno(*args, **kwargs)

    def flush(self, *args, **kwargs):
        return self._wrapped.flush(*args, **kwargs)

    def isatty(self, *args, **kwargs):
        return self._wrapped.isatty(*args, **kwargs)

    def readable(self, *args, **kwargs):
        return self._wrapped.readable(*args, **kwargs)

    def readline(self, size=-1, /):
        sleep(0)
        if size >= 0:
            size = min(self._read_limit, size)
        return self._wrapped.readline(size)

    def readlines(self, hint=-1, /):
        sleep(0)
        if hint >= 0:
            hint = min(self._read_limit, hint)
        return self._wrapped.readlines(hint)

    def seek(self, *args, **kwargs):
        return self._wrapped.seek(*args, **kwargs)

    def seekable(self, *args, **kwargs):
        return self._wrapped.seekable(*args, **kwargs)

    def tell(self, *args, **kwargs):
        return self._wrapped.tell(*args, **kwargs)

    def truncate(self, *args, **kwargs):
        return self._wrapped.truncate(*args, **kwargs)

    def writable(self, *args, **kwargs):
        return self._wrapped.writable(*args, **kwargs)

    def writelines(self, *args, **kwargs):
        sleep(0)
        return self._wrapped.writelines(*args, **kwargs)

    def __del__(self, *args, **kwargs):
        return self._wrapped.__del__(*args, **kwargs)

    def read(self, size=-1, /):
        sleep(0)
        if size >= 0:
            size = min(self._read_limit, size)
        return self._wrapped.read(size)

    def readall(self, *args, **kwargs):
        sleep(0)
        return self._wrapped.readall(*args, **kwargs)

    def readinto(self, *args, **kwargs):
        sleep(0)
        return self._wrapped.readinto(*args, **kwargs)

    def write(self, *args, **kwargs):
        sleep(0)
        return self._wrapped.write(*args, **kwargs)


class InterruptibleIOZipFile(ZipFile):
    """
    A ZipFile whose open method will return a InterruptibleRawIOWrapper-wrapped
    fileobj
    """

    def open(self, *args, **kwargs) -> RawIOBase:
        return InterruptibleRawIOWrapper(super().open(*args, **kwargs), read_limit=16_384)
