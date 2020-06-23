#!/usr/bin/env python3

import json
import socketserver
import subprocess
import sys
import tempfile
from http.server import *
from pathlib import Path
from shutil import copy
from typing import Optional, Tuple, Union

import requests


class Renderer:

    def __init__(self, path_to_generator: str):
        self.logo_path = Path(path_to_generator) / "examples" / "Latex_Logo.pdf"
        self.jar_path = Path(path_to_generator) / "target" / "Generator.jar"

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
                            "TimeSheetGenerator/target/TimeSheetGenerator-v0.2.2-jar-with-dependencies.jar",
                            "--file",
                            global_file.name,
                            month_file.name,
                            output_file.name
                        ])
                        if len(out) != 0:
                            return (f"Trans lation failed: {str(out)}", None)

                        with open(output_file.name, "r") as f:
                            return (None, f.read())
                    except subprocess.CalledProcessError as e:
                        return (f"Exit code {e.returncode}, message was {e.output}", None)

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
                        "-interaction=batchmode",
                        str(tex_file_path.resolve())
                    ],
                    cwd=tmpdir_name,
                    stderr=subprocess.DEVNULL
                )
                with open(Path(tmpdir_name, "Zettel.pdf"), "rb") as out:
                    return out.read()
            except subprocess.CalledProcessError as e:
                return f"Error generating pdf: {e.returncode}, Output: {e.output}"


USED_RENDERER: Renderer


class Handler(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_header("Content-type", "text; charset=utf-8")
        self.end_headers()

    def _send_error(self, text: str):
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(text.encode("UTF-8"))
        self.wfile.flush()

    def do_POST(self):
        content_len = int(self.headers.get('content-length', 0))
        data = json.loads(self.rfile.read(content_len))

        if "global_json" not in data or "month_json" not in data:
            self.send_response(400)
            return

        (error, latex) = USED_RENDERER.render_to_latex(data["global_json"], data["month_json"])

        if latex is None:
            self.send_error(400, "Failed to render to latex", error)
            return

        self.send_response(200)
        self.send_header("Content-type", "application/binary")
        self.end_headers()

        pdf_bytes = USED_RENDERER.render_latex(latex)

        if isinstance(pdf_bytes, str):
            self.send_error(400, "Failed to render latex to pdf", pdf_bytes)
            return

        self.wfile.write(pdf_bytes)
        self.wfile.flush()


def run(server_class=HTTPServer, handler_class=BaseHTTPRequestHandler, port=8080):
    server_address = ('127.0.0.1', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


def main(port: int, path_to_generator: str):
    global USED_RENDERER

    if not Path(path_to_generator).exists():
        print("Generator path does not exist", file=sys.stderr)
        exit(1)
    USED_RENDERER = Renderer(path_to_generator)
    run(HTTPServer, Handler, port)


if __name__ == '__main__':
    main(int(sys.argv[2]), sys.argv[1])
