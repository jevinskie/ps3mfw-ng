from contextlib import contextmanager
import io
from typing import Final, Optional
from typing_extensions import Self

from attrs import define, field
import requests
from wrapt import ObjectProxy


class SubscriptedIOBaseMixin:
    sz: int
    blksz: Optional[int]

    def __getitem__(self, item: slice) -> bytes:
        byte_off, num_bytes, step = item.start, item.stop, item.step
        if byte_off is None:
            byte_off = 0
        if num_bytes is None:
            num_bytes = self.sz
        if step == Ellipsis:
            byte_off, num_bytes = byte_off * self.blksz, num_bytes * self.blksz
        old_tell = self.tell()
        self.seek(byte_off, io.SEEK_SET)
        buf = self.read(num_bytes)
        self.seek(old_tell, io.SEEK_SET)
        return buf


class SeekContextIOBaseMixin:
    @contextmanager
    def seek_ctx(self, offset: int, whence: int = io.SEEK_SET) -> int:
        old_tell = self.tell()
        try:
            yield self.seek(offset, whence)
        finally:
            self.seek(old_tell)


class FancyRawIOBase(ObjectProxy, SubscriptedIOBaseMixin, SeekContextIOBaseMixin):
    pass


@define
class OffsetRawIOBase(SubscriptedIOBaseMixin, SeekContextIOBaseMixin):
    fh: Final[FancyRawIOBase] = field(converter=FancyRawIOBase)
    off: Final[int] = 0
    sz: Final[int] = -1
    blksz: Final[int] = 1
    _end: Final[int] = field(init=False)
    _parent_end: Final[int] = field(init=False)
    _idx: Final[int] = field(init=False, default=0)

    def __attrs_post_init__(self) -> None:
        with self.fh.seek_ctx(0, io.SEEK_END):
            self._parent_end = self.fh.tell()
        if self.sz == -1:
            self.sz = self._parent_end - self.off
        self._end = self.off + self.sz

    def read(self, size: int = -1) -> bytes:
        if size == -1:
            size = self.sz - self._idx
        if self._idx + size > self.sz:
            raise ValueError("out of bounds size")
        with self.fh.seek_ctx(self.off + self._idx, io.SEEK_SET):
            buf = self.fh.read(size)
        self._idx += len(buf)
        return buf

    def tell(self) -> int:
        return self._idx

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        parent_off = offset
        if whence == io.SEEK_SET:
            # add beginning gap
            parent_off += self.off
        elif whence == io.SEEK_END:
            # add end gap
            parent_off += self._parent_end - self._end
        self._idx = parent_off - self.off
        if not (0 <= self._idx <= self.sz):
            raise ValueError("out of bounds seek")
        return self._idx

    def subfile(self, offset: int, size: int = -1, blksz: Optional[int] = None) -> Self:
        suboff = self.off + offset
        if not (0 <= suboff <= self.sz):
            raise ValueError("subfile suboff out of range")
        if size < 0:
            size = self.sz - offset
        if blksz is None:
            blksz = self.blksz
        return type(self)(self.fh, suboff, size, blksz)


@define
class HTTPFile(FancyRawIOBase):
    url: Final[str]
    _ses: Final[requests.Session] = field(init=False, default=requests.Session())
    _idx: int = field(init=False, default=0)
    _sz: Final[int] = field(init=False)

    def __attrs_post_init__(self) -> None:
        head_r = self._ses.head(self.url)
        self._sz = int(head_r.headers["Content-Length"])

    def read(self, size: int = -1) -> bytes:
        if size == -1:
            size = self._sz - self._idx
        if self._idx + size > self._sz:
            raise ValueError("out of bounds size")
        buf = self._ses.get(self.url, headers={"Range": f"bytes={self._idx}-{self._idx + size - 1}"}).content
        assert len(buf) == size
        self._idx += size
        return buf

    def tell(self) -> int:
        return self._idx

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self._idx = offset
        elif whence == io.SEEK_CUR:
            self._idx += offset
        elif whence == io.SEEK_END:
            self._idx = self._sz
        if not (0 <= self._idx <= self._sz):
            raise ValueError("out of bounds seek")
        return self._idx
