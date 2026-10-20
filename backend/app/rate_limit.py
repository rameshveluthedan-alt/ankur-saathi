"""
A rate limit per network address for the few public actions that can be abused: signing in, registering a school, changing a PIN.

Why: the demo is public and its PINs are published. A PIN lockout protects one account, but it does not stop someone trying many accounts, and
every registration creates a school that can spend AI credits. This limits how often one address can try.

How the address is found: behind Cloud Run the header X-Forwarded-For is "whatever the client sent, then the address Google saw". Only the LAST
entry is trusted, because a client can write anything at the start. TRUSTED_PROXY_HOPS (default 1) says how many entries from the right belong
to Google's own proxies.

Limits: counted in memory, per container. With at most a few containers the effective limit is at most that many times higher, which is fine
for a demo; a shared store would be needed for more. A restart clears the counts. Pure ASGI, so it adds no cost to other requests.
"""

import json
import os
import time
from collections import deque

DEFAULT_RULES = [
    # (method, path, how many, per how many seconds, name shown in the message)
    ("POST", "/api/auth/login", int(os.environ.get("RATE_LOGIN_PER_MIN", "20")), 60, "sign-in"),
    ("POST", "/api/auth/register", int(os.environ.get("RATE_REGISTER_PER_HOUR", "5")), 3600, "registration"),
    ("POST", "/api/auth/change-pin", int(os.environ.get("RATE_CHANGE_PIN_PER_MIN", "10")), 60, "PIN change"),
]


def client_address(scope, hops: int = 1) -> str:
    """The address Google's front end saw. X-Forwarded-For: [anything the client wrote,] real address, [Google's own proxies]."""
    for name, value in scope.get("headers", []):
        if name == b"x-forwarded-for":
            parts = [p.strip() for p in value.decode("latin-1").split(",") if p.strip()]
            if parts:
                return parts[-hops] if len(parts) >= hops else parts[0]
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    def __init__(self, app, rules=None, hops=None, clock=time.monotonic):
        self.app = app
        self.rules = rules if rules is not None else DEFAULT_RULES
        self.hops = hops if hops is not None else int(os.environ.get("TRUSTED_PROXY_HOPS", "1"))
        self.clock = clock
        self.hits = {}                       # (rule index, address) -> timestamps within the window

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        method, path = scope["method"], scope["path"].rstrip("/")
        for i, (m, p, limit, window, label) in enumerate(self.rules):
            if method == m and path == p and limit > 0:
                key = (i, client_address(scope, self.hops))
                now = self.clock()
                q = self.hits.setdefault(key, deque())
                while q and now - q[0] > window:
                    q.popleft()
                if len(q) >= limit:
                    wait = max(1, int(window - (now - q[0])) + 1)
                    return await self._refuse(send, label, wait)
                q.append(now)
                if len(self.hits) > 20000:                              # a sweep, so that memory cannot grow without bound
                    for k in [k for k, v in self.hits.items() if not v or now - v[-1] > 3600]:
                        self.hits.pop(k, None)
                break
        await self.app(scope, receive, send)

    @staticmethod
    async def _refuse(send, label, wait):
        body = json.dumps({"detail": {"code": "rate_limited", "retry_after": wait,
                                      "message": f"बहुत ज़्यादा कोशिशें ({label}). कुछ देर बाद फिर कोशिश करें। (Too many attempts at {label}. Please wait and try again.)"}}, ensure_ascii=False).encode("utf-8")
        await send({"type": "http.response.start", "status": 429,
                    "headers": [(b"content-type", b"application/json; charset=utf-8"), (b"content-length", str(len(body)).encode()), (b"retry-after", str(wait).encode())]})
        await send({"type": "http.response.body", "body": body})


class SecurityHeadersMiddleware:
    """A few headers that cost nothing: no content-type guessing, no framing, no referrer, HTTPS only (Cloud Run is always HTTPS)."""
    HEADERS = [(b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"), (b"referrer-policy", b"no-referrer"),
               (b"strict-transport-security", b"max-age=31536000")]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                have = {k.lower() for k, _ in message.get("headers", [])}
                message = dict(message, headers=list(message.get("headers", [])) + [h for h in self.HEADERS if h[0] not in have])
            await send(message)
        await self.app(scope, receive, send_with_headers)
