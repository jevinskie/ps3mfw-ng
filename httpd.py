#!/usr/bin/env python3

from http.server import ThreadingHTTPServer

from tests.ps3mfw.http_ranges_server import RangeHTTPRequestHandler


def run(server_class=ThreadingHTTPServer, handler_class=RangeHTTPRequestHandler):
    server_address = ("", 38080)
    httpd = server_class(server_address, handler_class)
    httpd.RequestHandlerClass.quiet = False
    httpd.serve_forever()


if __name__ == "__main__":
    run()
