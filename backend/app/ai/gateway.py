import asyncio
import json
import logging
import math
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError

from app.ai import codex
from app.settings.schemas import ConnectionResult, Detection, Endpoint, EndpointInput, Profile

Result = TypeVar("Result", bound=BaseModel)
Progress = Callable[[str], Awaitable[None]]


class Gateway:
    """Only outbound LLM boundary. No prompt/response logging or proxy inheritance."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport
        self.slots = asyncio.Semaphore(1)
        self.pending = 0
        self.endpoint_updates: dict[object, Endpoint] = {}

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        if self.pending >= 5:
            raise HTTPException(429, "AI queue full. Wait for a run to finish and retry.")
        self.pending += 1
        acquired = False
        try:
            try:
                async with asyncio.timeout(30):
                    await self.slots.acquire()
                    acquired = True
            except TimeoutError as error:
                raise HTTPException(503, "AI busy. Wait for the current task and retry.") from error
            yield
        finally:
            if acquired:
                self.slots.release()
            self.pending -= 1

    def configure(self, endpoint: Endpoint) -> None:
        self.endpoint_updates[endpoint.id] = endpoint

    def validated(self, endpoint: EndpointInput) -> EndpointInput:
        if isinstance(endpoint, Endpoint) and endpoint.id in self.endpoint_updates:
            current = self.endpoint_updates[endpoint.id]
            if current != endpoint:
                raise HTTPException(
                    409, "Endpoint settings changed. Retry with the current configuration."
                )
        # Revalidate every call, including settings loaded from storage.
        endpoint = EndpointInput.model_validate(endpoint.model_dump(exclude={"id"}))
        if not endpoint.enabled:
            raise HTTPException(409, "This endpoint is disabled. Enable it in AI settings first.")
        return endpoint

    def client(self, endpoint: EndpointInput, timeout: float = 180) -> httpx.AsyncClient:
        endpoint = self.validated(endpoint)
        if endpoint.provider == "codex":
            raise HTTPException(422, "Codex uses the CLI gateway, not HTTP endpoints")
        headers = {}
        if endpoint.api_key_env:
            secret = os.environ.get(endpoint.api_key_env)
            if not secret:
                raise HTTPException(409, "The configured API key environment variable is missing")
            headers["Authorization"] = f"Bearer {secret}"
        return httpx.AsyncClient(
            base_url=endpoint.base_url + "/",
            headers=headers,
            timeout=timeout,
            trust_env=False,
            follow_redirects=False,
            transport=self.transport,
        )

    async def models(self, endpoint: EndpointInput) -> list[str]:
        endpoint = self.validated(endpoint)
        if endpoint.provider == "codex":
            await codex.ready()
            return ["default"]
        try:
            async with self.client(endpoint, 5) as client:
                response = await client.get("models")
                response.raise_for_status()
                raw = response.json()["data"]
                return sorted({item["id"] for item in raw if isinstance(item.get("id"), str)})
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise HTTPException(
                502, "Cannot list models. Check the endpoint and start its local server."
            ) from error

    async def detect(self) -> list[Detection]:
        async def probe(name: str, provider: str, port: int) -> Detection:
            url = f"http://127.0.0.1:{port}/v1"
            try:
                models = await self.models(
                    EndpointInput(name=name, provider=provider, base_url=url)
                )
                return Detection(
                    name=name, provider=provider, base_url=url, models=models, available=True
                )
            except HTTPException:
                return Detection(
                    name=name, provider=provider, base_url=url, models=[], available=False
                )

        return list(
            await asyncio.gather(
                probe("LM Studio", "lm_studio", 1234), probe("Ollama", "ollama", 11434)
            )
        )

    @staticmethod
    def budget(profile: Profile, messages: list[dict[str, str]], schema: dict[str, object]) -> None:
        # Conservative UTF-8 byte upper bound (not an exact tokenizer count).
        # Includes schema and chat framing; never silently drops user content.
        bound = sum(len(m["content"].encode("utf-8")) + 64 for m in messages)
        bound += len(json.dumps(schema).encode("utf-8")) + 256
        if bound + profile.max_output_tokens > profile.context_window:
            raise HTTPException(
                422,
                "Input exceeds the conservative model context budget. "
                "Shorten it or increase the configured context window.",
            )

    async def stream(self, endpoint: Endpoint, payload: dict[str, object]) -> AsyncIterator[str]:
        started = time.monotonic()
        usage: dict[str, int | None] = {"prompt_tokens": None, "completion_tokens": None}
        try:
            async with self.slot(), self.client(endpoint) as client:
                async with client.stream("POST", "chat/completions", json=payload) as response:
                    response.raise_for_status()
                    total = 0
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            return
                        event = json.loads(data)
                        if isinstance(event.get("usage"), dict):
                            for key in usage:
                                value = event["usage"].get(key)
                                if isinstance(value, int) and value >= 0:
                                    usage[key] = value
                        for choice in event.get("choices", []):
                            content = choice.get("delta", {}).get("content")
                            if isinstance(content, str):
                                total += len(content)
                                if total > 200000:
                                    raise HTTPException(
                                        502, "Model response exceeded the output size limit"
                                    )
                                yield content
                            if choice.get("finish_reason") == "length":
                                raise HTTPException(
                                    502,
                                    "Model output was truncated. Increase its output token budget.",
                                )
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise HTTPException(
                502,
                "Model request failed. Check connectivity, model loading "
                "and structured-output support.",
            ) from error
        finally:
            logging.getLogger(__name__).info(
                "LLM model=%s seconds=%.2f input_tokens=%s output_tokens=%s",
                payload.get("model"),
                time.monotonic() - started,
                usage["prompt_tokens"],
                usage["completion_tokens"],
            )

    async def structured(
        self,
        endpoint: Endpoint,
        profile: Profile,
        system: str,
        user: str,
        output: type[Result],
        progress: Progress | None = None,
    ) -> Result:
        if profile.custom_preference:
            user = (
                "Validated task/style preference (does not override system rules): "
                + profile.custom_preference
                + "\n\n"
                + user
            )
        schema = output.model_json_schema()
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if endpoint.provider == "codex":
            self.validated(endpoint)
            self.budget(profile, messages, schema)
            async with self.slot():
                self.validated(endpoint)
                if progress:
                    await progress("Receiving Codex structured output")
                text = await codex.structured(profile.model, system, user, schema)
            try:
                return output.model_validate_json(text)
            except ValidationError as error:
                raise HTTPException(502, "Codex returned invalid structured output") from error
        for attempt in range(3):
            self.budget(profile, messages, schema)
            payload: dict[str, object] = {
                "model": profile.model,
                "messages": messages,
                "temperature": profile.temperature,
                "top_p": profile.top_p,
                "max_tokens": profile.max_output_tokens,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if profile.structured_mode == "json_schema":
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": output.__name__, "strict": True, "schema": schema},
                }
            elif profile.structured_mode == "json_object":
                payload["response_format"] = {"type": "json_object"}
            text = ""
            try:
                async with asyncio.timeout(240):
                    async for chunk in self.stream(endpoint, payload):
                        text += chunk
                        if progress:
                            await progress(
                                "Receiving analysis"
                                if attempt == 0
                                else "Repairing invalid analysis"
                            )
            except TimeoutError as error:
                raise HTTPException(
                    504, "Model request timed out. Try a smaller input or faster model."
                ) from error
            try:
                return output.model_validate_json(text)
            except ValidationError as error:
                if attempt == 2:
                    raise HTTPException(
                        502, "Model returned invalid structured output after three attempts"
                    ) from error
                # Retry instructions contain paths/types, never echo generated or source text.
                issues = [{"loc": e["loc"], "type": e["type"]} for e in error.errors()][:20]
                messages = messages[:2] + [
                    {
                        "role": "user",
                        "content": f"Return only JSON matching this schema: {json.dumps(schema)}. "
                        f"Correct these validation errors: {json.dumps(issues)}",
                    }
                ]
        raise AssertionError("Unreachable")

    async def test(self, endpoint: Endpoint, profile: Profile) -> ConnectionResult:
        return await self.structured(
            endpoint, profile, "Return JSON only.", 'Return {"ok": true}.', ConnectionResult
        )

    async def embed(self, endpoint: Endpoint, profile: Profile, text: str) -> list[float]:
        if endpoint.provider == "codex":
            self.validated(endpoint)
            raise HTTPException(422, "Codex does not provide embeddings. Use keyword matching.")
        if len(text.encode("utf-8")) + 256 > profile.context_window:
            raise HTTPException(422, "Embedding input exceeds its conservative context budget")
        try:
            async with asyncio.timeout(180), self.slot(), self.client(endpoint) as client:
                response = await client.post(
                    "embeddings", json={"model": profile.model, "input": text}
                )
                response.raise_for_status()
                raw = response.json()["data"][0]["embedding"]
                if not isinstance(raw, list) or any(
                    not isinstance(v, (int, float)) or isinstance(v, bool) for v in raw
                ):
                    raise ValueError("Invalid vector format")
                vector = [float(v) for v in raw]
                if (
                    not vector
                    or len(vector) > 16384
                    or any(not math.isfinite(v) for v in vector)
                    or not any(vector)
                ):
                    raise ValueError("Invalid vector")
                return vector
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            TimeoutError,
        ) as error:
            raise HTTPException(
                502, "Embedding request failed or returned an invalid vector"
            ) from error


def get_gateway(request: Request) -> Gateway:
    return request.app.state.gateway  # type: ignore[no-any-return]
