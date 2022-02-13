
import bz2
import enum
import io
import lzma
from pathlib import Path
from typing import Final, Optional, Collection, BinaryIO, Mapping
import zlib

from anytree import RenderTree
from attrs import define, field
from construct import *
from construct import (
    Optional as ConstructOptional,
    Mapping as ConstructMapping,
)
from typing import Optional, Mapping
from fs.base import FS
from fs.enums import ResourceType
from fs.errors import *
from fs.info import Info
from fs.permissions import Permissions
from fs.subfs import SubFS
from fs.opener.errors import *
from fs.opener.parse import ParseResult
import fs.opener.registry
import untangle


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

PUPHeader = Struct(
    "magic" / Const(b"SCEUF\0\0"),
    "format_flag" / Byte,
    "package_version" / Int64ub,
    "image_version" / Int64ub,
    "segment_num" / Int64ub,
    "header_length" / Hex(Int64ub),
    "data_length" / Hex(Int64ub),
)
