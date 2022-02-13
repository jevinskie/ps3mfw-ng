import importlib.resources
from contextlib import nullcontext

from .http_ranges_server import http_server

from ps3mfw.io import HTTPFile
from ps3mfw.pup import PUP

def test_pup():
    with http_server():
    # with nullcontext():
        url = "https://archive.org/download/ps3updat-cex-3.55/ps3updat-cex-3.55.pup"
        url = "http://localhost:38080/tests/ps3mfw/ps3updat-cex-3.55.pup"
        fh = HTTPFile(url)
        # pup_path = importlib.resources.files(__package__) / "ps3updat-cex-3.55.pup"
        # fh = open(pup_path, 'rb')
        pup = PUP.parse_stream(fh)
        print(pup)
