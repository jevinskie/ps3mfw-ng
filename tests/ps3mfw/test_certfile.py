import importlib.resources
from contextlib import nullcontext
from pathlib import Path

import pytest

from ps3mfw.certfile import CertFile
from ps3mfw.io_extras import HTTPFile
from ps3mfw.pup import PUPFS

from .http_ranges_server import http_server

CWD = Path(__file__).parent


def test_certfile_ps3swu():
    pytest.skip()
    with http_server(directory=CWD):
        # with nullcontext():
        # url = "https://archive.org/download/ps3updat-cex-3.55/ps3updat-cex-3.55.pup"
        url = "http://localhost:38080/ps3updat-cex-3.55.pup"
        pupfh = HTTPFile(url)
        # pup_path = importlib.resources.files(__package__) / "ps3updat-cex-3.55.pup"
        # FIXME: missing refcnt incr? PUPFS(open()) doesn't work, closed file error
        # pupfh = open(pup_path, 'rb')
        pupfs = PUPFS(pupfh)
        slf_fh = pupfs.open("/ps3swu.self", "rb")
        slf = CertFile.parse_stream(slf_fh)
        # print(slf)


def test_certfile_default_spp():
    spp_path = importlib.resources.files(__package__) / "default.spp"
    # FIXME: missing refcnt incr? PUPFS(open()) doesn't work, closed file error
    sppfh = open(spp_path, "rb")
    spp = CertFile.parse_stream(sppfh)
    print(spp)
