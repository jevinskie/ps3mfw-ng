import importlib.resources
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
import threading

from .http_ranges_server import RangeHTTPRequestHandler

from ps3mfw.io import HTTPFile
from ps3mfw.pup import PUP

@contextmanager
def http_server(server_class=ThreadingHTTPServer, handler_class=RangeHTTPRequestHandler):
    server_address = ('', 38080)
    httpd = server_class(server_address, handler_class)
    try:
        threading.Thread(target = lambda: httpd.serve_forever()).start()
        yield
    finally:
        httpd.shutdown()
    print("done serving")

def test_pup():
    with http_server():
        # url = "https://archive.org/download/ps3updat-cex-3.55/ps3updat-cex-3.55.pup"
        # url = "https://ia801402.us.archive.org/8/items/ps3updat-cex-3.15/ps3updat-cex-3.15.pup"
        url = "http://localhost:38080/tests/ps3mfw/ps3updat-cex-3.55.pup"
        fh = HTTPFile(url)
        # etc_xar_path = importlib.resources.files(__package__) / "ps3updat-cex-3.55.pup"
        # fh = open(etc_xar_path, 'rb')
        pup = PUP.parse_stream(fh)
        print(pup)
