import bz2
import enum
import io
import lzma
import zlib
from pathlib import Path
from typing import BinaryIO, Collection, Final, Mapping, Optional

import fs.opener.registry
import untangle
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

segid2name = {
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
