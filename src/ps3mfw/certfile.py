import enum
import io
from typing import BinaryIO, Collection, Final, Mapping, Optional

from attrs import define, field
from construct import Mapping as ConstructMapping
from construct import Optional as ConstructOptional
from construct import *

from .io import FancyRawIOBase

from typing import Mapping, Optional  # isort:skip


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

CertFileHeader = Struct(
    "magic" / Const(b"SCE\0"),
    "version" / Int32ub,
)

CertFile = Struct(
    "header" / CertFileHeader,
)


@define
class CertifiedFile:
    fh: Final[FancyRawIOBase] = field(converter=FancyRawIOBase)
    cf: Final[Struct] = field(init=False)

    def __attrs_post_init__(self):
        with self.fh.seek_ctx(0):
            self.cf = CertFile.parse_stream(self.fh)
