#!/usr/bin/env python3

import importlib.resources
from contextlib import nullcontext
from pathlib import Path

from ps3mfw.io_extras import HTTPFile
from ps3mfw.pup import PUP, PUPFile

from .http_ranges_server import http_server

CWD = Path(__file__).parent


def test_pup_struct_parse():
    # with nullcontext():
    with http_server(directory=CWD):
        # url = "https://archive.org/download/ps3updat-cex-3.55/ps3updat-cex-3.55.pup"
        url = "http://localhost:38080/ps3updat-cex-3.55.pup"
        fh = HTTPFile(url)
        # pup_path = importlib.resources.files(__package__) / "ps3updat-cex-3.55.pup"
        # fh = open(pup_path, 'rb')
        pup = PUP.parse_stream(fh)
        assert pup.header.data_length == 0xAA9_A440
        assert pup.header_digest.digest == bytes.fromhex(
            "9CBC7D85CEAF24B16BFAA360F03AA0005681EA4D"
        )


def test_pupfile():
    with http_server(directory=CWD):
        # with nullcontext():
        url = "http://localhost:38080/ps3updat-cex-3.55.pup"
        fh = HTTPFile(url)
        # pup_path = importlib.resources.files(__package__) / "ps3updat-cex-3.55.pup"
        # fh = open(pup_path, 'rb')
        pupf = PUPFile(fh)
        pupf.rootfs.dump()


if __name__ == "__main__":
    test_pupfile()
