"""Shared HTTP client with HTTP/2, JWT auth, and retry logic."""
from __future__ import annotations

import asyncio
from typing import Optional, Any

import httpx

from . import logger
from .headers import get_headers
from .captcha import detect as detect_captcha

log = logger.get("HTTP")

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


class SessionExpiredError(Exception):
    """Raised when session/auth token is expired."""
    pass


class HTTPClient:
    """Shared HTTP/2 client with JWT auth, connection pooling, and retry logic."""

    def __init__(
        self,
        cookies: str = "",
        auth_token: Optional[str] = None,
        csrf_token: Optional[str] = None,
        proxy: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.cookies = cookies
        self.auth_token = auth_token
        self.csrf_token = csrf_token
        self.proxy = proxy
        self._client: Optional[httpx.AsyncClient] = None
        self._timeout = httpx.Timeout(timeout, connect=10.0)
        self._limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0,
        )

    async def __aenter__(self) -> "HTTPClient":
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def start(self) -> None:
        """Initialize the client."""
        if self._client is None:
            # Log auth status
            if self.auth_token:
                log.debug("HTTP client initialized with Bearer auth")
            else:
                log.warning("HTTP client initialized without auth token")

            # Build client kwargs (only include proxies if set)
            client_kwargs = {
                "http2": True,
                "timeout": self._timeout,
                "limits": self._limits,
                "follow_redirects": True,
            }
            if self.proxy:
                client_kwargs["proxies"] = self.proxy

            self._client = httpx.AsyncClient(**client_kwargs)

    async def close(self) -> None:
        """Close the client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the underlying client."""
        if self._client is None:
            raise RuntimeError("Client not started. Call start() first.")
        return self._client

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        json: Optional[dict] = None,
        data: Optional[Any] = None,
        retries: int = MAX_RETRIES,
        request_type: str = "api",
    ) -> httpx.Response:
        """
        Make request with retry logic, auth, and error handling.

        Args:
            method: HTTP method
            url: Request URL
            headers: Additional headers to merge
            json: JSON body
            data: Form data
            retries: Max retry attempts
            request_type: 'api', 'page', or 'checkout' for header profiles

        Returns:
            httpx.Response

        Raises:
            SessionExpiredError: If 401/403 indicates auth failure
        """
        # Build headers with auth token
        req_headers = get_headers(
            cookies=self.cookies,
            auth_token=self.auth_token,
            csrf_token=self.csrf_token,
            request_type=request_type if not json else "api",
        )
        if headers:
            req_headers.update(headers)

        last_error: Optional[Exception] = None

        for attempt in range(retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    json=json,
                    data=data,
                )

                # Auth failure - session expired
                if response.status_code in [401, 403]:
                    log.warning(f"Auth failure ({response.status_code}) - session may be expired")
                    # Only raise on first attempt to allow caller to handle
                    if attempt == 0:
                        raise SessionExpiredError(
                            f"Auth failed with {response.status_code}. Re-login required."
                        )
                    # On retry, just continue
                    await asyncio.sleep(1)
                    continue

                # Rate limited - back off
                if response.status_code == 429:
                    wait = BACKOFF_BASE ** (attempt + 1)
                    log.warning(f"Rate limited, waiting {wait}s...")
                    await asyncio.sleep(wait)
                    continue

                # Server error - retry
                if response.status_code >= 500:
                    wait = BACKOFF_BASE ** attempt
                    log.warning(f"Server error {response.status_code}, retry in {wait}s")
                    await asyncio.sleep(wait)
                    continue

                # CAPTCHA detected
                if detect_captcha(response):
                    log.warning("CAPTCHA detected in response")
                    # Return response so caller can handle CAPTCHA
                    return response

                return response

            except SessionExpiredError:
                # Don't retry auth failures - let caller handle
                raise

            except httpx.TimeoutException:
                last_error = httpx.TimeoutException(f"Timeout on attempt {attempt + 1}")
                log.warning(f"Timeout (attempt {attempt + 1}/{retries})")
                await asyncio.sleep(1)

            except httpx.RequestError as e:
                last_error = e
                log.warning(f"Request error: {e} (attempt {attempt + 1}/{retries})")
                await asyncio.sleep(1)

        log.error(f"All {retries} attempts failed for {url}")
        raise last_error or Exception("Request failed")

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST request."""
        return await self.request("POST", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    def update_auth(self, auth_token: str, csrf_token: Optional[str] = None) -> None:
        """Update auth tokens after session refresh."""
        self.auth_token = auth_token
        if csrf_token:
            self.csrf_token = csrf_token
        log.info("Auth tokens updated")
