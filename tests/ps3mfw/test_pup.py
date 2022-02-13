from ps3mfw.io import HTTPFile
from ps3mfw import pup

def test_pup():
    url = "https://archive.org/download/ps3updat-cex-3.55/ps3updat-cex-3.55.pup"
    fh = HTTPFile(url)
    pup_hdr = pup.PUPHeader.parse_stream(fh)
    print(pup_hdr)
