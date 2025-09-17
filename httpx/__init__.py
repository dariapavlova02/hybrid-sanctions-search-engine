"""Lightweight httpx stub for test environments without the real dependency."""

from __future__ import annotations

import json as _json
from types import SimpleNamespace
from typing import Any, Callable, Dict, Optional, Sequence
from urllib.parse import urljoin, urlparse


class HTTPStatusError(Exception):
    """Raised when a response indicates failure."""

    def __init__(self, message: str, response: "Response") -> None:
        super().__init__(message)
        self.response = response


class Auth:
    """Base authentication placeholder."""

    def auth_flow(self, request: "Request"):
        yield request


class BasicAuth(Auth):
    """Simple username/password auth container."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password


class Timeout:
    """Timeout configuration stub."""

    def __init__(self, timeout: float, connect: Optional[float] = None) -> None:
        self.read = timeout
        self.write = timeout
        self.pool = timeout
        self.connect = timeout if connect is None else connect


class URL:
    """Parsed URL exposing components used in tests."""

    def __init__(self, url: str) -> None:
        parsed = urlparse(url)
        self.raw = url
        self.scheme = parsed.scheme
        self.host = parsed.hostname
        self.port = parsed.port
        self.path = parsed.path or "/"
        self.query = parsed.query

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.raw


class Request:
    """HTTP request container used by MockTransport handlers."""

    def __init__(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Any = None,
        content: Optional[bytes] = None,
    ) -> None:
        self.method = method.upper()
        self.url = URL(url)
        self.headers = headers or {}
        self._json = json
        if content is None and json is not None:
            self._content = _json.dumps(json).encode("utf-8")
        else:
            self._content = content

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        if self._content:
            return _json.loads(self._content.decode("utf-8"))
        raise ValueError("No JSON payload available")

    @property
    def content(self) -> Optional[bytes]:
        return self._content


class Response:
    """HTTP response stub with minimal helpers."""

    def __init__(
        self,
        status_code: int,
        *,
        json: Any = None,
        text: Optional[str] = None,
        content: Optional[bytes] = None,
    ) -> None:
        self.status_code = status_code
        self._json = json
        if content is not None:
            self._content = content
        elif text is not None:
            self._content = text.encode("utf-8")
        elif json is not None:
            self._content = _json.dumps(json, ensure_ascii=False).encode("utf-8")
        else:
            self._content = b""

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        if self._content:
            return _json.loads(self._content.decode("utf-8"))
        return None

    @property
    def text(self) -> str:
        return self._content.decode("utf-8")

    def raise_for_status(self) -> None:
        if not self.is_success:
            raise HTTPStatusError(f"HTTP {self.status_code}", self)


class AsyncBaseTransport:
    """Base transport interface."""

    async def handle_async(self, request: Request) -> Response:
        raise NotImplementedError

    async def aclose(self) -> None:  # pragma: no cover - optional cleanup
        return None


class MockTransport(AsyncBaseTransport):
    """Transport that routes requests to a user handler."""

    def __init__(self, handler: Callable[[Request], Response]) -> None:
        self._handler = handler

    async def handle_async(self, request: Request) -> Response:
        return self._handler(request)


class AsyncClient:
    """Extremely small subset of httpx.AsyncClient used in tests."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Auth] = None,
        timeout: Optional[Timeout | float] = None,
        verify: Optional[Any] = None,
        transport: Optional[AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = base_url or ""
        self.headers = headers or {}
        self.auth = auth
        self.timeout = timeout
        self.verify = verify
        self._transport = transport

    async def _send(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[Any] = None,
    ) -> Response:
        full_url = self._build_url(url)
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)
        request = Request(method, full_url, headers=request_headers, json=json)

        if self._transport is None:
            raise RuntimeError("No transport configured for AsyncClient stub")

        response = await self._transport.handle_async(request)
        return response

    def _build_url(self, url: str) -> str:
        if not self.base_url:
            return url
        return urljoin(self.base_url.rstrip("/") + "/", url.lstrip("/"))

    async def get(self, url: str, **kwargs: Any) -> Response:
        return await self._send("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> Response:
        return await self._send("POST", url, **kwargs)

    async def close(self) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._transport is not None:
            await self._transport.aclose()


__all__ = [
    "AsyncClient",
    "AsyncBaseTransport",
    "Auth",
    "BasicAuth",
    "HTTPStatusError",
    "MockTransport",
    "Request",
    "Response",
    "Timeout",
]
