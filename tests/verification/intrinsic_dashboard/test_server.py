from __future__ import annotations

import http.client
import gzip
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from email.message import Message
from http import HTTPStatus
from io import BytesIO

import pytest

from src.workflow.verification.intrinsic_dashboard.server import (
    DashboardHTTPServer,
    DashboardRequestHandler,
    create_server,
)


@contextmanager
def running_server(
    state_provider,
    elementwise_provider=lambda: {"schema_version": 1, "available": False},
) -> Iterator[tuple[DashboardHTTPServer, int]]:
    try:
        server = create_server(
            port=0,
            state_provider=state_provider,
            elementwise_provider=elementwise_provider,
        )
    except PermissionError as error:
        pytest.skip(f"sandbox forbids binding a loopback test port: {error}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def request(
    port: int,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def recording_handler(
    accept_encoding: str,
) -> tuple[DashboardRequestHandler, dict[str, str]]:
    handler = object.__new__(DashboardRequestHandler)
    handler.headers = Message()
    handler.headers["Accept-Encoding"] = accept_encoding
    handler.wfile = BytesIO()
    recorded: dict[str, str] = {}
    handler.send_response = lambda status: recorded.__setitem__("Status", str(status))
    handler.send_header = lambda name, value: recorded.__setitem__(name, value)
    handler.end_headers = lambda: None
    return handler, recorded


def test_server_is_loopback_only_and_serves_injected_state() -> None:
    calls = 0

    def provide_state() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"revision": "abc123", "intrinsics": []}

    with running_server(provide_state) as (server, port):
        assert server.server_address[0] == "127.0.0.1"

        status, headers, body = request(port, "GET", "/api/state?fresh=1")
        assert status == 200
        assert json.loads(body) == {"revision": "abc123", "intrinsics": []}
        assert calls == 1
        assert headers["Content-Type"] == "application/json; charset=utf-8"
        assert "no-store" in headers["Cache-Control"]
        assert headers["Pragma"] == "no-cache"
        assert headers["Vary"] == "Accept-Encoding"

        status, headers, body = request(port, "GET", "/api/health")
        assert status == 200
        assert json.loads(body) == {"status": "ok"}
        assert calls == 1
        assert "no-store" in headers["Cache-Control"]


@pytest.mark.parametrize(
    ("path", "content_type", "needle"),
    [
        ("/", "text/html; charset=utf-8", b"<!doctype html>"),
        ("/index.html", "text/html; charset=utf-8", b"Intrinsic verification"),
        ("/styles.css", "text/css; charset=utf-8", b":root"),
        ("/app.js", "text/javascript; charset=utf-8", b'"use strict"'),
        ("/elementwise.js", "text/javascript; charset=utf-8", b'"use strict"'),
    ],
)
def test_server_serves_only_the_dashboard_assets(
    path: str, content_type: str, needle: bytes
) -> None:
    with running_server(lambda: {}) as (_, port):
        status, headers, body = request(port, "GET", path)
        assert status == 200
        assert headers["Content-Type"] == content_type
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "no-store" in headers["Cache-Control"]
        assert needle in body


@pytest.mark.parametrize(
    "path",
    [
        "/unknown",
        "/web/index.html",
        "/%2e%2e/server.py",
        "/static/../index.html",
        "/%5c..%5cserver.py",
    ],
)
def test_server_rejects_unknown_and_traversal_paths(path: str) -> None:
    with running_server(lambda: {}) as (_, port):
        status, headers, body = request(port, "GET", path)
        assert status in {400, 404}
        assert headers["Content-Type"] == "application/json; charset=utf-8"
        assert json.loads(body)["error"]


@pytest.mark.parametrize(
    "method",
    ["HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"],
)
def test_server_rejects_non_get_methods(method: str) -> None:
    with running_server(lambda: {}) as (_, port):
        status, headers, body = request(port, method, "/api/state")
        assert status == 405
        assert headers["Allow"] == "GET"
        if method == "HEAD":
            assert body == b""
        else:
            assert json.loads(body) == {"error": "method not allowed"}


def test_state_failure_is_generic_and_does_not_stop_server() -> None:
    def fail() -> object:
        raise RuntimeError("private filesystem detail")

    with running_server(fail) as (_, port):
        status, _, body = request(port, "GET", "/api/state")
        assert status == 500
        assert b"private filesystem detail" not in body
        assert json.loads(body) == {"error": "dashboard state is unavailable"}

        status, _, body = request(port, "GET", "/api/health")
        assert status == 200
        assert json.loads(body) == {"status": "ok"}


def test_elementwise_endpoint_uses_the_injected_artifact_provider() -> None:
    graph = {"schema_version": 1, "available": True, "programs": [{"program_id": "held-out"}]}
    with running_server(lambda: {}, lambda: graph) as (_, port):
        status, headers, body = request(port, "GET", "/api/elementwise")
        assert status == 200
        assert headers["Content-Type"] == "application/json; charset=utf-8"
        assert json.loads(body) == graph


def test_large_state_is_gzipped_only_when_the_client_accepts_it() -> None:
    state = {"revision": "abc123", "payload": "x" * 4096}

    with running_server(lambda: state) as (_, port):
        status, headers, body = request(
            port,
            "GET",
            "/api/state",
            headers={"Accept-Encoding": "br, gzip"},
        )
        assert status == 200
        assert headers["Content-Encoding"] == "gzip"
        assert headers["Vary"] == "Accept-Encoding"
        assert json.loads(gzip.decompress(body)) == state
        assert int(headers["Content-Length"]) == len(body)
        assert "no-store" in headers["Cache-Control"]

        status, headers, body = request(
            port,
            "GET",
            "/api/state",
            headers={"Accept-Encoding": "gzip;q=0, *;q=1"},
        )
        assert status == 200
        assert "Content-Encoding" not in headers
        assert headers["Vary"] == "Accept-Encoding"
        assert json.loads(body) == state


def test_gzip_encoding_without_a_loopback_socket() -> None:
    handler, headers = recording_handler("br, gzip")
    original = (json.dumps({"payload": "x" * 4096}) + "\n").encode("ascii")

    handler._send_bytes(
        HTTPStatus.OK,
        original,
        "application/json; charset=utf-8",
        allow_gzip=True,
    )

    encoded = handler.wfile.getvalue()
    assert headers["Content-Encoding"] == "gzip"
    assert headers["Vary"] == "Accept-Encoding"
    assert int(headers["Content-Length"]) == len(encoded)
    assert gzip.decompress(encoded) == original
    assert "no-store" in headers["Cache-Control"]


def test_explicit_gzip_rejection_overrides_the_wildcard() -> None:
    handler, headers = recording_handler("gzip;q=0, *;q=1")
    original = b"x" * 4096

    handler._send_bytes(
        HTTPStatus.OK,
        original,
        "application/json; charset=utf-8",
        allow_gzip=True,
    )

    assert "Content-Encoding" not in headers
    assert headers["Vary"] == "Accept-Encoding"
    assert handler.wfile.getvalue() == original


def test_small_state_is_not_gzipped_but_varies_on_accept_encoding() -> None:
    with running_server(lambda: {"revision": "small"}) as (_, port):
        status, headers, body = request(
            port,
            "GET",
            "/api/state",
            headers={"Accept-Encoding": "gzip"},
        )
        assert status == 200
        assert "Content-Encoding" not in headers
        assert headers["Vary"] == "Accept-Encoding"
        assert json.loads(body) == {"revision": "small"}


@pytest.mark.parametrize("port", [-1, 65536, True, 1.5])
def test_create_server_rejects_invalid_ports(port: object) -> None:
    with pytest.raises(ValueError, match="port"):
        create_server(port=port, state_provider=lambda: {})  # type: ignore[arg-type]
