"""
Auth0 Token Vault integration for Amanat.

Uses Auth0's federated token exchange to securely obtain service-specific
access tokens via Token Vault. This lets the agent call OneDrive,
Slack, etc. on behalf of the user without ever seeing their
raw credentials.

In demo mode: returns synthetic tokens for offline development.
In live mode: exchanges Auth0 tokens for federated connection tokens.
"""

import os
import httpx
from dataclasses import dataclass, field


# Token Vault connection names (must match Auth0 dashboard)
CONNECTIONS = {
    "onedrive": {
        "connection": "microsoft-graph",
        "scopes": ["Files.Read", "Files.ReadWrite", "offline_access"],
    },
    "outlook": {
        "connection": "microsoft-graph",
        "scopes": ["Mail.Read", "offline_access"],
    },
    "slack": {
        "connection": "sign-in-with-slack",
        "scopes": ["channels:read", "channels:history", "search:read"],
    },
    "github": {
        "connection": "github",
        "scopes": [],
    },
}


@dataclass
class TokenInfo:
    """Represents an access token from Token Vault."""
    access_token: str
    token_type: str = "Bearer"
    scope: str = ""
    connection: str = ""
    expires_in: int = 3600


@dataclass
class UserSession:
    """Represents an authenticated user session."""
    user_id: str
    email: str
    name: str
    org: str = ""
    auth0_token: str = ""
    refresh_token: str = ""
    connected_services: list[str] = field(default_factory=list)
    tokens: dict[str, TokenInfo] = field(default_factory=dict)


class Auth0TokenVault:
    """
    Token Vault client using OAuth 2.0 Token Exchange (RFC 8693).

    In demo mode: returns synthetic tokens and a fake user session.
    In live mode: exchanges the user's Auth0 access token for
    service-specific tokens via Token Vault connections.
    """

    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.domain = os.environ.get("AUTH0_DOMAIN", "")
        self.client_id = os.environ.get("AUTH0_CLIENT_ID", "")
        self.client_secret = os.environ.get("AUTH0_CLIENT_SECRET", "")
        self._session: UserSession | None = None

    def create_session(
        self,
        user_id: str,
        email: str,
        name: str,
        auth0_token: str = "",
        refresh_token: str = "",
    ) -> UserSession:
        """Create a session from OAuth callback data."""
        if self.demo_mode:
            self._session = UserSession(
                user_id="demo|12345",
                email="josha@hrc-hyrule.org",
                name="Josha Deepdelve",
                org="Hyrule Restoration Commission",
                connected_services=["onedrive", "slack"],
                tokens={
                    "slack": TokenInfo(
                        access_token="demo-slack-token",
                        connection="sign-in-with-slack",
                        scope="channels:read channels:history",
                    ),
                },
            )
            return self._session

        self._session = UserSession(
            user_id=user_id,
            email=email,
            name=name,
            auth0_token=auth0_token,
            refresh_token=refresh_token,
            connected_services=list(CONNECTIONS.keys()),
        )
        return self._session

    def exchange_token(self, service: str) -> TokenInfo:
        """
        Exchange the user's Auth0 token for a federated service token
        via Auth0 Token Vault.

        POST https://{domain}/oauth/token
        grant_type=urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token
        subject_token={auth0_access_token}
        subject_token_type=urn:ietf:params:oauth:token-type:access_token
        requested_token_type=http://auth0.com/oauth/token-type/federated-connection-access-token
        connection={connection_name}
        """
        if not self._session:
            raise RuntimeError("No active session. Call create_session() first.")

        if self.demo_mode:
            return self._session.tokens.get(service, TokenInfo(
                access_token=f"demo-{service}-token",
                connection=CONNECTIONS.get(service, {}).get("connection", ""),
            ))

        conn_config = CONNECTIONS.get(service)
        if not conn_config:
            raise ValueError(f"Unknown service: {service}")

        token_url = f"https://{self.domain}/oauth/token"

        # Prefer refresh token (required for Token Vault federated exchange)
        if self._session.refresh_token:
            subject_token = self._session.refresh_token
            subject_token_type = "urn:ietf:params:oauth:token-type:refresh_token"
        else:
            subject_token = self._session.auth0_token
            subject_token_type = "urn:ietf:params:oauth:token-type:access_token"

        payload = {
            "grant_type": "urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "subject_token": subject_token,
            "subject_token_type": subject_token_type,
            "requested_token_type": "http://auth0.com/oauth/token-type/federated-connection-access-token",
            "connection": conn_config["connection"],
        }

        if conn_config["scopes"]:
            payload["scope"] = " ".join(conn_config["scopes"])

        response = httpx.post(token_url, data=payload)

        if response.status_code != 200:
            error = response.json()
            raise PermissionError(
                f"Token Vault exchange failed for {service}: "
                f"{error.get('error_description', error.get('error', 'unknown'))}"
            )

        data = response.json()
        token = TokenInfo(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope", ""),
            connection=conn_config["connection"],
            expires_in=data.get("expires_in", 3600),
        )

        self._session.tokens[service] = token
        return token

    def get_token(self, service: str) -> TokenInfo:
        """Get a cached token or exchange for a new one."""
        if not self._session:
            raise RuntimeError("No active session.")

        # Return cached token if available
        if service in self._session.tokens:
            return self._session.tokens[service]

        # Otherwise exchange
        return self.exchange_token(service)

    @property
    def session(self) -> UserSession | None:
        return self._session

    def get_consent_summary(self) -> dict:
        """Return a summary of what the user has consented to."""
        if not self._session:
            return {"authenticated": False}

        return {
            "authenticated": True,
            "user": self._session.name,
            "email": self._session.email,
            "org": self._session.org,
            "connected_services": [
                {
                    "service": svc,
                    "connection": CONNECTIONS[svc]["connection"],
                    "scope": " ".join(CONNECTIONS[svc]["scopes"]),
                    "status": "connected" if svc in self._session.tokens else "pending",
                }
                for svc in self._session.connected_services
                if svc in CONNECTIONS
            ],
        }
