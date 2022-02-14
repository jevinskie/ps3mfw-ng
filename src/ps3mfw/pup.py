import enum
from typing import BinaryIO, Collection, Final, Mapping, Optional

import fs.opener.registry
from anytree import RenderTree
from attrs import define, field
from construct import Mapping as ConstructMapping
from construct import Optional as ConstructOptional
from construct import *
from typing import Mapping, Optional
from fs.base import FS
from fs.enums import ResourceType
from fs.errors import *
from fs.info import Info
from fs.opener.errors import *
from fs.opener.parse import ParseResult
from fs.permissions import Permissions
from fs.subfs import SubFS
import wrapt

from .io import FancyRawIOBase, OffsetRawIOBase
from .fs import INode, DirEntType

segid2filename = {
    0x100: "version.txt",
    0x101: "license.xml",
    0x102: "promo_flags.txt",
    0x103: "update_flags.txt",
    0x104: "patch_build.txt",
    0x200: "ps3swu.self",
    0x201: "vsh.tar",
    0x202: "dots.txt",
    0x203: "patch_data.pkg",
    0x300: "update_files.tar",
    0x501: "spkg_hdr.tar",
    0x601: "ps3swu2.self",
}

def get_seg_filename(segid):
    if segid in segid2filename:
        return segid2filename[segid]
    return f"seg_{segid:#x}.bin"


class SignAlgorithmEnum(enum.IntEnum):
    hmac_sha1 = 0
    hmac_sha256 = 1


SignAlgorithm = Enum(Int32ub, SignAlgorithmEnum)

PUPHeader = Struct(
    "magic" / Const(b"SCEUF\0\0"),
    "format_flag" / Byte,
    "package_version" / Int64ub,
    "image_version" / Int64ub,
    "segment_num" / Int64ub,
    "header_length" / Hex(Int64ub),
    "data_length" / Hex(Int64ub),
)

PUPSegmentEntry = Struct(
    "id" / Int64ub,
    "offset" / Hex(Int64ub),
    "size" / Hex(Int64ub),
    "sign_algorithm" / SignAlgorithm,
    "padding" / Padding(4),
)

PUPDigestEntry = Struct(
    "segment_index" / Int64ub,
    "digest" / Hex(Byte[20]),
    "padding" / Padding(4),
)

PUPHeaderDigest = Struct(
    "digest" / Hex(Byte[20]),
)

PUP = Struct(
    "header" / PUPHeader,
    "segment_table" / PUPSegmentEntry[this.header.segment_num],
    "digest_table" / PUPDigestEntry[this.header.segment_num],
    "header_digest" / PUPHeaderDigest,
)

# @wrapt.patch_function_wrapper("ps3mfw.pup", "PUP.parse_stream")
# def PUP_parse_stream_patched(parse_stream, self, args, kwargs):
#     r = parse_stream(*args, **kwargs)
#     r.rootfs = INode.root_node()
#     return r


# class PUP(wrapt.ObjectProxy):
#     # def __new__(cls, *args, **kwargs):
#     #     return wrapt.ObjectProxy(wrapped=PUP, *args, *kwargs)
#
#     def __init__(self, *args, **kwargs):
#         self = wrapt.ObjectProxy(wrapped=PUP)
#         # new_self = wrapt.ObjectProxy(wrapped=PUP)
#         # new_self.__init__(self, *args, *kwargs)
#         # self = new_self
#
#     def parse_stream(self, stream, **contextkw):
#         raise NotImplementedError

# PUP2 = wrapt.ObjectProxy(PUP)

class PUP2(type(PUP)):
    # def __new__(cls, *args, **kwargs):
    #     return wrapt.ObjectProxy(PUP.__new__(*args, **kwargs))

    def __init__(self, *args, **kwargs):
        PUP.__init__(*args, **kwargs)
        self = wrapt.ObjectProxy(self)

# class PUP2(PUP):
#     def __init__(self, *args, **kwargs):
#         super(PUP, self).__init__(*args, **kwargs)


# class PUP2(wrapt.ObjectProxy, PUP):
#     def parse_stream(self, stream, **contextkw):
#         r = super().parse_stream(stream, **contextkw)
#         r.rootfs = INode.root_node()
#         return r


@define
class PUPFile:
    fh: Final[FancyRawIOBase] = field(converter=FancyRawIOBase)
    pup: PUP2 = field(init=False)
    rootfs: Final[INode] = field(init=False)

    def __attrs_post_init__(self):
        with self.fh.seek_ctx(0):
            self.pup = PUP2.parse_stream(self.fh)
        print(f"pup: {self.pup.header}")
        print(f"pup: {self.pup.rootfs}")


@define
class PUPFS(fs.base.FS):
    file: Final[FancyRawIOBase]
    pup: Final[PUPFile] = field(init=False)

    def __attrs_post_init__(self):
        if not isinstance(self.file, BinaryIO):
            self.file = FancyRawIOBase(io.FileIO(self.file, 'r'))
        self.pup = PUPFile(self.file)

    def getinfo(self, path: str, namespaces: Optional[Collection[str]] = None) -> Info:
        ino = self.pup.rootfs.lookup(path)
        if ino is None:
            raise ResourceNotFound(path)
        return Info({"basic": {"name": ino.name, "is_dir": ino.is_dir},
                     "details": {"type": ino.pyfs_type, "size": ino.size}})

    def listdir(self, path: str) -> [str]:
        ino = self.pup.rootfs.lookup(path)
        if ino is None:
            raise ResourceNotFound(path)
        return [ino.name for ino in ino.children]

    def makedir(self, path: str, permissions: Optional[Permissions] = None, recreate: bool = False) -> SubFS[FS]:
        raise NotWriteable("PUP supports only reading")

    def openbin(self, path: str, mode: str = "r", buffering: int = -1, **kwargs) -> BinaryIO:
        raise NotImplementedError

    def remove(self, path: str) -> None:
        raise NotWriteable("PUP supports only reading")

    def removedir(self, path: str) -> None:
        raise NotWriteable("PUP supports only reading")

    def setinfo(self, path: str, info: Mapping[str, Mapping[str, object]]) -> None:
        raise NotWriteable("PUP supports only reading")


class PUPFSOpener(fs.opener.Opener):
    protocols = ["pup"]

    def open_fs(self, fs_url: str, parse_result: ParseResult, writeable: bool, create: bool, cwd: str):
        if create or writeable:
            # FIXME
            raise NotWriteable("PUP supports only reading")
        return PUPFS(parse_result.resource)
