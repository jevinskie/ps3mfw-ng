import enum
import io
from typing import BinaryIO, Collection, Final, Mapping, Optional

from attrs import define, field
from construct import Mapping as ConstructMapping
from construct import Optional as ConstructOptional
from construct import *

from .io_extras import FancyRawIOBase

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


class CategoryEnum(enum.IntEnum):
    SELF = 1
    SRVK = 2
    SPKG = 3
    SSPP = 4


Category = Enum(Int16ub, CategoryEnum)

CertFileHeader = Struct(
    "magic" / Const(b"SCE\0"),
    "version" / Int32ub,
    "attribute" / Int16ub,
    "category" / Category,
    "ext_header_size" / Int32ub,
    "file_offset" / Int64ub,
    "file_size" / Int64ub,
)

EncryptionRootHeader = Struct(
    "key" / Bytes(16),
    "key_pad" / Bytes(16),
    "iv" / Bytes(16),
    "iv_pad" / Bytes(16),
)


class SignAlgorithmEnum(enum.IntEnum):
    ECDSA160 = 1
    HMAC_SHA1 = 2
    SHA1 = 3
    RSA2048 = 5


SignAlgorithm = Enum(Int32ub, SignAlgorithmEnum)

CertificationHeader = Struct(
    "sign_offset" / Int64ub,
    "sign_algorithm" / SignAlgorithm,
    "cert_entry_number" / Int32ub,
    "attr_entry_num" / Int32ub,
    "optional_header_size" / Int32ub,
    "pad" / Padding(8),
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
