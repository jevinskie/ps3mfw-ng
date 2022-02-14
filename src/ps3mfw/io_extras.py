import io
import mmap
from array import array
from contextlib import contextmanager
from typing import Final, Optional

import requests
from attrs import define, field
from typing_extensions import Self
from wrapt import ObjectProxy

from .util import round_down, round_up


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
        # import pydevd
        # pydevd.settrace()
        old_tell = self.tell()
        try:
            yield self.seek(offset, whence)
        finally:
            self.seek(old_tell)


class FancyRawIOBase(SubscriptedIOBaseMixin, SeekContextIOBaseMixin):
    pass


class FancyRawIOBaseProxy(ObjectProxy, FancyRawIOBase):
    def __new__(cls, wrapped):
        if isinstance(wrapped, FancyRawIOBase):
            return wrapped
        return super().__new__(cls)

    def __init__(self, wrapped):
        if isinstance(wrapped, io.BufferedReader):
            super().__init__(wrapped.raw)
        elif isinstance(wrapped, io.RawIOBase):
            super().__init__(wrapped)
        elif isinstance(wrapped, str):
            super().__init__(io.FileIO(wrapped, "r"))
        else:
            raise NotImplementedError


@define
class OffsetRawIOBase(io.RawIOBase, FancyRawIOBase):
    fh: Final[FancyRawIOBase] = field(converter=FancyRawIOBaseProxy)
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
        size = min(self.sz - self._idx, size)
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
            raise IndexError("out of bounds seek")
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


@define(slots=False)
class HTTPFile(FancyRawIOBase):
    url: Final[str]
    blksz: Final[int] = 256 * 1024
    _ses: Final[requests.Session] = field(init=False, default=requests.Session())
    _idx: int = field(init=False, default=0)
    _sz: Final[int] = field(init=False)
    _cache: Final[mmap.mmap] = field(init=False)
    _cache_blkmap: Final[array] = field(init=False)

    def __attrs_post_init__(self) -> None:
        head_r = self._ses.head(self.url, allow_redirects=True)
        assert (
            "accept-ranges" in head_r.headers
            and "bytes" in head_r.headers["Accept-Ranges"]
        )
        self._sz = int(head_r.headers["Content-Length"])
        self._cache = mmap.mmap(-1, self._sz)
        self._cache_blkmap = array("Q")
        blkmap_num_words = (
            round_up(self._sz, self.blksz)
            // self.blksz
            // self._cache_blkmap.itemsize
            // 8
        )
        self._cache_blkmap.extend([0 for i in range(blkmap_num_words)])

    def _is_cached(self, byte_off: int) -> bool:
        word_idx = byte_off // self.blksz // self._cache_blkmap.itemsize // 8
        packed = self._cache_blkmap[word_idx]
        bit_idx = (byte_off // self.blksz) % (self._cache_blkmap.itemsize * 8)
        return packed & (1 << bit_idx) != 0

    def _mark_cached(self, byte_off: int) -> None:
        word_idx = byte_off // self.blksz // self._cache_blkmap.itemsize // 8
        bit_idx = (byte_off // self.blksz) % (self._cache_blkmap.itemsize * 8)
        self._cache_blkmap[word_idx] |= 1 << bit_idx

    def read(self, size: int = -1) -> bytes:
        if size == -1:
            size = self._sz - self._idx
        if self._idx + size > self._sz:
            raise IndexError("out of bounds size")
        blk_byte_start, blk_byte_end = round_down(self._idx, self.blksz), round_up(
            self._idx + size, self.blksz
        )
        blk_byte_sz = blk_byte_end - blk_byte_start
        blk_start, blk_end = blk_byte_start // self.blksz, blk_byte_end // self.blksz
        # FIXME: coalesce uncached regions and fetch in a single request
        for blk in range(blk_start, blk_end):
            if self._is_cached(blk * self.blksz):
                continue
            range_str = f"bytes={blk * self.blksz}-{(blk + 1) * self.blksz - 1}"
            cache_fill_buf = self._ses.get(
                self.url, headers={"Range": range_str}
            ).content
            assert len(cache_fill_buf) == self.blksz
            self._cache[blk * self.blksz : (blk + 1) * self.blksz] = cache_fill_buf
            self._mark_cached(blk * self.blksz)
        res = self._cache[self._idx : self._idx + size]
        self._idx += size
        return res

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
            raise IndexError("out of bounds seek")
        return self._idx
