import importlib.resources
from contextlib import nullcontext
from pathlib import Path

from .http_ranges_server import http_server

from ps3mfw.io import HTTPFile
from ps3mfw.pup import PUPFS
from ps3mfw.certfile import CertFile

CWD = Path(__file__).parent

def test_certfile():
    with http_server(directory=CWD):
    # with nullcontext():
        # url = "https://archive.org/download/ps3updat-cex-3.55/ps3updat-cex-3.55.pup"
        url = "http://localhost:38080/ps3updat-cex-3.55.pup"
        pupfh = HTTPFile(url)
        # pup_path = importlib.resources.files(__package__) / "ps3updat-cex-3.55.pup"
        # FIXME: missing refcnt incr? PUPFS(open()) doesn't work, closed file error
        # pupfh = open(pup_path, 'rb')
        pupfs = PUPFS(pupfh)
        slf_fh = pupfs.open('/ps3swu.self', 'rb')
        slf = CertFile.parse_stream(slf_fh)
        print(slf)
