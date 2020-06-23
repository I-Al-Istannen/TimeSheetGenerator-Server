#!/usr/bin/env python3

from http.server import *
import socketserver
import sys
import requests


class Handler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/calendar; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        response = requests.get("https://campus.kit.edu/sp/webcal/" + self.path)
        fixed = fix_encoding(response.content.decode("utf-8"))
        self.wfile.write(fixed.encode("utf-8"))

    def do_HEAD(self):
        self._set_headers()


def run(server_class=HTTPServer, handler_class=BaseHTTPRequestHandler, port=8080):
    server_address = ('127.0.0.1', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


def main(port):
    run(HTTPServer, Handler, port)


if __name__ == '__main__':
    main(int(sys.argv[1]))
