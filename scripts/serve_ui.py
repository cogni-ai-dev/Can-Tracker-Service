#!/usr/bin/env python3
from __future__ import annotations

import argparse
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UIProxyHandler(BaseHTTPRequestHandler):
    api_host: str
    api_port: int
    html_path: Path

    def log_message(self, fmt: str, *args: object) -> None:
        print("ui-proxy:", fmt % args, flush=True)

    def do_GET(self) -> None:
        self.route()

    def do_POST(self) -> None:
        self.route()

    def do_PATCH(self) -> None:
        self.route()

    def do_DELETE(self) -> None:
        self.route()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
        self.end_headers()

    def route(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self.serve_html()
            return
        if self.path.startswith("/api/"):
            self.proxy_api()
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def serve_html(self) -> None:
        try:
            data = self.html_path.read_bytes()
        except FileNotFoundError:
            message = f"UI file not found: {self.html_path}".encode()
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def proxy_api(self) -> None:
        body = self.rfile.read(int(self.headers.get("content-length", "0") or "0"))
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "content-length", "connection"}
        }
        conn = HTTPConnection(self.api_host, self.api_port, timeout=30)
        try:
            conn.request(self.command, self.path, body=body or None, headers=headers)
            response = conn.getresponse()
            data = response.read()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in {"transfer-encoding", "connection", "content-length"}:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            data = str(exc).encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        finally:
            conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the standalone CAN Tracker UI and proxy /api to the API.")
    parser.add_argument("--host", default="127.0.0.1", help="UI bind host.")
    parser.add_argument("--port", type=int, default=8081, help="UI bind port.")
    parser.add_argument("--api-host", default="127.0.0.1", help="API host for proxying /api requests.")
    parser.add_argument("--api-port", type=int, default=8001, help="API port for proxying /api requests.")
    parser.add_argument(
        "--html",
        type=Path,
        default=ROOT / "can_tracker_dashboard.html",
        help="Standalone HTML file to serve.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    handler = type(
        "ConfiguredUIProxyHandler",
        (UIProxyHandler,),
        {
            "api_host": args.api_host,
            "api_port": args.api_port,
            "html_path": args.html.resolve(),
        },
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(
        f"UI proxy running at http://{args.host}:{args.port} "
        f"(proxying /api to http://{args.api_host}:{args.api_port})",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
