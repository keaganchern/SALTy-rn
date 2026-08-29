"""Loopback-only HTTP server for the intrinsic verification dashboard."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import threading
from collections.abc import Callable, Mapping, Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
WEB_ROOT = Path(__file__).resolve().parent / "web"

StateProvider = Callable[[], Any]

_STATIC_FILES: Mapping[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/elementwise.js": ("elementwise.js", "text/javascript; charset=utf-8"),
}
_MALFORMED_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_GZIP_MINIMUM_BYTES = 1024
_DEFAULT_PROVIDER: StateProvider | None = None
_DEFAULT_ELEMENTWISE_PROVIDER: StateProvider | None = None
_DEFAULT_PROVIDER_LOCK = threading.Lock()


def _default_state_provider() -> Any:
    """Resolve and cache the production scanner only on the first API request."""

    global _DEFAULT_PROVIDER
    if _DEFAULT_PROVIDER is None:
        with _DEFAULT_PROVIDER_LOCK:
            if _DEFAULT_PROVIDER is None:
                from .state import create_state_provider

                _DEFAULT_PROVIDER = create_state_provider()
    return _DEFAULT_PROVIDER()


def _default_elementwise_provider() -> Any:
    """Resolve the artifact-graph projection only when its endpoint is read."""

    global _DEFAULT_ELEMENTWISE_PROVIDER
    if _DEFAULT_ELEMENTWISE_PROVIDER is None:
        with _DEFAULT_PROVIDER_LOCK:
            if _DEFAULT_ELEMENTWISE_PROVIDER is None:
                from .elementwise_graph import create_elementwise_provider

                _DEFAULT_ELEMENTWISE_PROVIDER = create_elementwise_provider()
    return _DEFAULT_ELEMENTWISE_PROVIDER()


class DashboardHTTPServer(ThreadingHTTPServer):
    """A threaded server carrying immutable dashboard configuration."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        port: int,
        state_provider: StateProvider,
        elementwise_provider: StateProvider,
        web_root: Path = WEB_ROOT,
    ) -> None:
        self.state_provider = state_provider
        self.elementwise_provider = elementwise_provider
        self.web_root = web_root.resolve(strict=True)
        super().__init__((DEFAULT_HOST, port), DashboardRequestHandler)


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Serve the fixed dashboard assets and its read-only JSON API."""

    server: DashboardHTTPServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = self._request_path()
        if path is None:
            return

        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        if path == "/api/state":
            try:
                state = self.server.state_provider()
                encoded = self._encode_json(state)
            except Exception:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "dashboard state is unavailable"},
                )
                return
            self._send_bytes(
                HTTPStatus.OK,
                encoded,
                "application/json; charset=utf-8",
                allow_gzip=True,
            )
            return
        if path == "/api/elementwise":
            try:
                state = self.server.elementwise_provider()
                encoded = self._encode_json(state)
            except Exception:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "elementwise artifact graph is unavailable"},
                )
                return
            self._send_bytes(
                HTTPStatus.OK,
                encoded,
                "application/json; charset=utf-8",
                allow_gzip=True,
            )
            return

        static_file = _STATIC_FILES.get(path)
        if static_file is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        filename, content_type = static_file
        candidate = (self.server.web_root / filename).resolve(strict=False)
        if candidate.parent != self.server.web_root:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            content = candidate.read_bytes()
        except OSError:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "dashboard asset is unavailable"},
            )
            return
        self._send_bytes(HTTPStatus.OK, content, content_type)

    def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._method_not_allowed()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._method_not_allowed()

    def do_PUT(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._method_not_allowed()

    def do_PATCH(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._method_not_allowed()

    def do_DELETE(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._method_not_allowed()

    def do_OPTIONS(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._method_not_allowed()

    def do_TRACE(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._method_not_allowed()

    def do_CONNECT(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._method_not_allowed()

    def _request_path(self) -> str | None:
        if _MALFORMED_ESCAPE.search(self.path):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid request path"})
            return None

        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid request path"})
            return None
        try:
            path = unquote(parsed.path, errors="strict")
        except UnicodeDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid request path"})
            return None

        components = path.split("/")
        if (
            not path.startswith("/")
            or "\\" in path
            or "\x00" in path
            or any(component in {".", ".."} for component in components)
        ):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid request path"})
            return None
        return path

    def _method_not_allowed(self) -> None:
        content = b'{"error":"method not allowed"}\n'
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", "GET")
        self._send_common_headers("application/json; charset=utf-8", len(content))
        self.end_headers()
        self.wfile.write(content)

    @staticmethod
    def _encode_json(value: Any) -> bytes:
        return (
            json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
            + "\n"
        ).encode("ascii")

    def _send_json(self, status: HTTPStatus, value: Any) -> None:
        self._send_bytes(
            status,
            self._encode_json(value),
            "application/json; charset=utf-8",
        )

    def _accepts_gzip(self) -> bool:
        """Return whether the client explicitly permits gzip content coding."""

        header = self.headers.get("Accept-Encoding")
        if not header:
            return False
        accepted: dict[str, float] = {}
        for item in header.split(","):
            parts = [part.strip() for part in item.split(";")]
            coding = parts[0].lower()
            if not coding:
                continue
            quality = 1.0
            for parameter in parts[1:]:
                name, separator, value = parameter.partition("=")
                if separator and name.strip().lower() == "q":
                    try:
                        quality = float(value.strip())
                    except ValueError:
                        quality = 0.0
            accepted[coding] = quality if 0.0 <= quality <= 1.0 else 0.0
        if "gzip" in accepted:
            return accepted["gzip"] > 0.0
        return accepted.get("*", 0.0) > 0.0

    def _send_bytes(
        self,
        status: HTTPStatus,
        content: bytes,
        content_type: str,
        *,
        allow_gzip: bool = False,
    ) -> None:
        content_encoding: str | None = None
        if allow_gzip and len(content) >= _GZIP_MINIMUM_BYTES and self._accepts_gzip():
            content = gzip.compress(content, mtime=0)
            content_encoding = "gzip"
        self.send_response(status)
        if allow_gzip:
            self.send_header("Vary", "Accept-Encoding")
        if content_encoding is not None:
            self.send_header("Content-Encoding", content_encoding)
        self._send_common_headers(content_type, len(content))
        self.end_headers()
        self.wfile.write(content)

    def _send_common_headers(self, content_type: str, content_length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; img-src 'self'; "
            "script-src 'self'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'",
        )


def create_server(
    *,
    port: int = DEFAULT_PORT,
    state_provider: StateProvider | None = None,
    elementwise_provider: StateProvider | None = None,
) -> DashboardHTTPServer:
    """Create a loopback-only server; ``port=0`` asks the OS for a test port."""

    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("port must be an integer in the range 0..65535")
    provider = _default_state_provider if state_provider is None else state_provider
    elementwise = (
        _default_elementwise_provider
        if elementwise_provider is None
        else elementwise_provider
    )
    return DashboardHTTPServer(port, provider, elementwise)


def serve(
    *,
    port: int = DEFAULT_PORT,
    state_provider: StateProvider | None = None,
) -> None:
    """Run the dashboard until interrupted, closing its socket on exit."""

    server = create_server(port=port, state_provider=state_provider)
    try:
        host, actual_port = server.server_address[:2]
        print(f"Intrinsic dashboard: http://{host}:{actual_port}/")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(
    argv: Sequence[str] | None = None,
    *,
    state_provider: StateProvider | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    arguments = parser.parse_args(argv)
    serve(port=arguments.port, state_provider=state_provider)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
