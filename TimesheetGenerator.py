#!/usr/bin/env python3

import html
import json
import os
import socketserver
import subprocess
import sys
import tempfile
from http import HTTPStatus
from http.server import *
from pathlib import Path
from shutil import copy
from typing import Optional, Tuple, Union

import requests


class Renderer:

    def __init__(self, path_to_generator: str):
        self.logo_path = Path(path_to_generator) / "Latex_Logo.pdf"
        self.jar_path = Path(path_to_generator) / "Generator.jar"

    def render_to_latex(self, global_json: str, month_json: str) -> Tuple[Optional[str], Optional[str]]:
        with tempfile.NamedTemporaryFile(mode="w+") as global_file:
            with tempfile.NamedTemporaryFile(mode="w+") as month_file:
                with tempfile.NamedTemporaryFile() as output_file:
                    global_file.write(global_json)
                    global_file.flush()
                    month_file.write(month_json)
                    month_file.flush()

                    try:
                        out = subprocess.check_output([
                            "java",
                            "-jar",
                            str(self.jar_path.resolve()),
                            "--file",
                            global_file.name,
                            month_file.name,
                            output_file.name
                        ])
                        if len(out) != 0:
                            return (f"Translation failed: {out.decode('UTF-8')}", None)

                        with open(output_file.name, "r") as f:
                            return (None, f.read())
                    except subprocess.CalledProcessError as e:
                        print("Command that failed was ", e.cmd)
                        return (f"Exit code {e.returncode}, message was {e.output.decode('UTF-8')}", None)

    def render_latex(self, latex: str) -> Union[bytes, str]:
        with tempfile.TemporaryDirectory() as tmpdir_name:
            tex_file_path = Path(tmpdir_name, "Zettel.tex")
            with open(tex_file_path, "w") as f:
                f.write(latex)

            copy(self.logo_path, Path(tmpdir_name, "Latex_Logo.pdf"))

            try:
                subprocess.check_output(
                    [
                        "latexmk",
                        "-pdf",
                        "-interaction=nonstopmode",
                        str(tex_file_path.resolve())
                    ],
                    cwd=tmpdir_name,
                    stderr=subprocess.DEVNULL
                )
                with open(Path(tmpdir_name, "Zettel.pdf"), "rb") as out:
                    return out.read()
            except subprocess.CalledProcessError as e:
                return f"Error generating pdf: {e.returncode}, Output: {e.output.decode('UTF-8')}"


USED_RENDERER: Renderer


class Handler(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_header("Content-type", "text; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_HEAD(self):
        self._set_headers()

    def send_error(self, code, message=None, explain=None):
        """Send and log an error reply.

        Arguments are
        * code:    an HTTP error code
                   3 digits
        * message: a simple optional 1 line reason phrase.
                   *( HTAB / SP / VCHAR / %x80-FF )
                   defaults to short entry matching the response code
        * explain: a detailed message defaults to the long entry
                   matching the response code.

        This sends an error response (so it must be called before any
        output has been generated), logs the error, and finally sends
        a piece of HTML explaining the error to the user.

        """

        try:
            shortmsg, longmsg = self.responses[code]
        except KeyError:
            shortmsg, longmsg = '???', '???'
        if message is None:
            message = shortmsg
        if explain is None:
            explain = longmsg
        self.log_error("code %d, message %s", code, message)
        self.send_response(code, message)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Connection', 'close')

        # Message body is omitted for cases described in:
        #  - RFC7230: 3.3. 1xx, 204(No Content), 304(Not Modified)
        #  - RFC7231: 6.3.6. 205(Reset Content)
        body = None
        if (code >= 200 and
            code not in (HTTPStatus.NO_CONTENT,
                         HTTPStatus.RESET_CONTENT,
                         HTTPStatus.NOT_MODIFIED)):
            # HTML encode to prevent Cross Site Scripting attacks
            # (see bug #1100201)
            content = (self.error_message_format % {
                'code': code,
                'message': html.escape(message, quote=False),
                'explain': html.escape(explain, quote=False)
            })
            body = content.encode('UTF-8', 'replace')
            self.send_header("Content-Type", self.error_content_type)
            self.send_header('Content-Length', str(len(body)))
        self.end_headers()

        if self.command != 'HEAD' and body:
            self.wfile.write(body)

    def do_POST(self):
        print("Handling post")
        content_len = int(self.headers.get('content-length', 0))
        data = json.loads(self.rfile.read(content_len))

        if "global_json" not in data or "month_json" not in data:
            self.send_response(400)
            return

        (error, latex) = USED_RENDERER.render_to_latex(data["global_json"], data["month_json"])

        if latex is None:
            print("Failed to render to latex", error)
            self.send_error(400, "Failed to render to latex", error)
            return

        self.send_response(200)
        self.send_header("Content-type", "application/binary")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        pdf_bytes = USED_RENDERER.render_latex(latex)

        if isinstance(pdf_bytes, str):
            self.send_error(400, "Failed to render latex to pdf", pdf_bytes)
            return

        self.wfile.write(pdf_bytes)
        self.wfile.flush()


def run(server_class=HTTPServer, handler_class=BaseHTTPRequestHandler, port=8080):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


def main(port: int, path_to_generator: str):
    global USED_RENDERER

    if not Path(path_to_generator).exists():
        print("Generator path does not exist", file=sys.stderr)
        exit(1)
    print("Running server on port", port)
    USED_RENDERER = Renderer(path_to_generator)
    run(HTTPServer, Handler, port)


if __name__ == '__main__':
    main(int(sys.argv[2]), sys.argv[1])
