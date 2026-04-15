from collections.abc import Iterable, Iterator
from io import RawIOBase
from time import sleep
from typing import Any, Self, TypeVar
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

    def __init__(self, wrapped, read_limit=4_096):
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
        return InterruptibleRawIOWrapper(super().open(*args, **kwargs), read_limit=8_192)


InterruptibleIterAny = TypeVar("InterruptibleIterAny", bound="InterruptibleIter[Any]")


class InterruptibleIter[T]:
    _inner_iterator: Iterator[T]
    _boxed_counter: list[int]
    _interruptible_every: int

    def __init__(
        self,
        iterable: Iterable[T],
        *,
        interruptible_every: int | None = None,
        sync_with: InterruptibleIterAny | None = None,
    ):
        """
        Given an `iterable`, will yield its contents, calling sleep(0) before yielding each `interruptible_every`'th
        iteration. Can alternatively be provided with a `sync_with` argument which will share the counter from
        another InterruptibleIter and inherit its interruptible_every value.
        """
        self._inner_iterator = iter(iterable)

        if interruptible_every is None == sync_with is None:
            raise TypeError("Must specify interruptible_every or sync_with (and not both)")

        if interruptible_every is not None:
            self._interruptible_every = interruptible_every
            self._boxed_counter = [0]
        else:
            self._interruptible_every = sync_with._interruptible_every
            self._boxed_counter = sync_with._boxed_counter

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> T:
        ret = next(self._inner_iterator)

        if self._boxed_counter[0] >= self._interruptible_every:
            sleep(0)
            self._boxed_counter[0] = 0

        self._boxed_counter[0] += 1

        return ret
