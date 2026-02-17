"""FreeAgent."""

import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

import ngrok
from oauthlib.oauth2 import WebApplicationClient
from requests_oauthlib import OAuth2Session

if TYPE_CHECKING:
    from collections.abc import Iterator
    from socket import socket


class FreeAgent(OAuth2Session):  # type: ignore[misc]
    """FreeAgent client."""

    def __init__(
        self,
        oauth_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """FreeAgent client."""
        self._token: dict[str, str | int | float] | None = None
        self._token_path = Path(".freeagent-token")
        super().__init__(
            *args,
            client=WebApplicationClient(client_id=oauth_id),
            token=self.load_token(),
            token_updater=self.save_token,
            auto_refresh_url="https://api.freeagent.com/v2/token_endpoint",
            **kwargs,
        )

    def get_authorization_url(self, listener: FreeAgentAuthCodeListener) -> str:
        """Get authorization URL."""
        self.redirect_uri = listener.ngrok.url()
        url: str = self._client.prepare_request_uri(
            "https://api.freeagent.com/v2/approve_app", redirect_uri=self.redirect_uri
        )
        return url

    def fetch_token(self, *args: Any, **kwargs: Any) -> dict[str, str | int | float]:
        """Fetch token, and save it."""
        token: dict[str, str | int | float] = super().fetch_token(*args, **kwargs)
        self.save_token(token)
        return token

    def load_token(self) -> dict[str, str | int | float]:
        """Load OAuth token."""
        if self._token is None:
            if not self._token_path.exists():
                with self._token_path.open(mode="w") as fp:
                    json.dump({}, fp)

            with self._token_path.open(mode="r") as fp:
                self._token = json.load(fp)

        return self._token

    def save_token(self, token: dict[str, str | int | float]) -> None:
        """Save an OAuth token."""
        self._token = token
        with self._token_path.open("w") as fp:
            json.dump(self._token, fp)

    def get_projects(self) -> Iterator[dict[str, Any]]:
        """Get all projects."""
        response = self.get("https://api.freeagent.com/v2/projects")
        response.raise_for_status()
        response_data = response.json()
        yield from response_data["projects"]

    def get_project(self, url: str) -> dict[str, Any]:
        """Get a project."""
        response = self.get(url)
        response.raise_for_status()
        response_data = response.json()
        project: dict[str, Any] = response_data["project"]
        return project

    def get_tasks(
        self, *, load_projects: bool = False, **kwargs: Any
    ) -> Iterator[dict[str, Any]]:
        """Get all tasks."""
        response = self.get("https://api.freeagent.com/v2/tasks", params=kwargs)
        response.raise_for_status()
        response_data = response.json()
        tasks = response_data["tasks"]
        for task in tasks:
            if load_projects:
                task["project"] = self.get_project(task["project"])

            yield task

    def create_timeslip(self, timeslip: dict[str, Any]) -> None:
        """Create timeslip."""
        response = self.post(
            "https://api.freeagent.com/v2/timeslips", json={"timeslip": timeslip}
        )
        response.raise_for_status()

    def get_logged_in_user(self) -> dict[str, Any]:
        """Get the logged in user."""
        response = self.get("https://api.freeagent.com/v2/users/me")
        response.raise_for_status()
        response_data = response.json()
        user: dict[str, Any] = response_data["user"]
        return user


class FreeAgentAuthCodeListener(HTTPServer):
    """OAuth HTTP server."""

    def __init__(self, ngrok_domain: str | None) -> None:
        """OAuth HTTP server."""
        port = random.randint(49152, 65535)  # noqa: S311
        super().__init__(("", port), OAuthHTTPRequestHandler)
        self.last_path: str | None = None
        self.ngrok = ngrok.forward(
            f"localhost:{port}", authtoken_from_env=True, domain=ngrok_domain
        )

    def wait_for_auth_code(self) -> str:
        """Wait for an HTTP request, which will contain the auth code."""
        self.handle_request()
        return parse_qs(str(urlparse(self.last_path).query))["code"][0]


class OAuthHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth listening."""

    def __init__(
        self,
        request: socket,
        client_address: tuple[str, int],
        server: FreeAgentAuthCodeListener,
    ) -> None:
        """HTTP request handler for OAuth listening."""
        super().__init__(request, client_address, server)
        server.last_path = self.path

    def do_GET(self) -> None:  # noqa: N802
        """Send response to GET request."""
        body = bytes("You can close this window now.", "utf-8")
        self.protocol_version = "HTTP/1.1"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
