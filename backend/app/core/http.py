"""Bound ingress before parsing JSON; attach privacy headers even on errors."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 4 * 1024 * 1024


class PrivateHTTP:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def private_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                for name, value in (
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                ):
                    headers = [(k, v) for k, v in headers if k.lower() != name]
                    headers.append((name, value))
                message["headers"] = headers
            await send(message)

        if scope["method"] in {"POST", "PUT", "PATCH", "DELETE"}:
            headers = dict(scope["headers"])
            try:
                length = int(headers.get(b"content-length", b"0"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY_BYTES:
                await JSONResponse({"detail": "Request body exceeds the 4 MiB limit"}, 413)(
                    scope, receive, private_send
                )
                return
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    await JSONResponse({"detail": "Request body exceeds the 4 MiB limit"}, 413)(
                        scope, receive, private_send
                    )
                    return
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def bounded_receive() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, bounded_receive, private_send)
        else:
            await self.app(scope, receive, private_send)
