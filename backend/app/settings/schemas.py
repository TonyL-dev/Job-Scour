import ipaddress
import re
from typing import Literal, Self
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import Field, model_validator

from app.career.schemas import Contract

Task = Literal[
    "job_analysis",
    "embeddings",
    "ranking",
    "rewriting",
    "summary",
    "verification",
    "condensing",
    "import_extraction",
    "profile_questions",
    "cover_letter",
]


class EndpointInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    provider: Literal["codex", "lm_studio", "ollama", "openai_compatible"]
    base_url: str
    remote_consent: bool = False
    enabled: bool = True
    api_key_env: str | None = None

    @model_validator(mode="after")
    def destination(self) -> Self:
        if self.provider == "codex":
            if self.base_url != "https://chatgpt.com/codex" or self.api_key_env:
                raise ValueError(
                    "Codex uses the installed CLI's ChatGPT login, not a URL or API key"
                )
            if self.enabled and not self.remote_consent:
                raise ValueError("Codex requires explicit consent to send supplied data to OpenAI")
            return self
        url = urlsplit(self.base_url)
        if url.scheme not in {"http", "https"} or not url.hostname:
            raise ValueError("Use an HTTP(S) OpenAI-compatible base URL")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("Credentials, query strings and fragments are not allowed in URLs")
        host = url.hostname.lower()
        if host == "localhost":
            host = "127.0.0.1"
        try:
            local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = False
        if not local and (url.scheme != "https" or (self.enabled and not self.remote_consent)):
            raise ValueError("Remote endpoints require HTTPS and explicit data-sharing consent")
        if self.api_key_env and not re.fullmatch(r"LLM_[A-Z0-9_]+", self.api_key_env):
            raise ValueError("API keys must reference an LLM_* environment variable")
        netloc = f"[{host}]" if ":" in host else host
        if url.port:
            netloc += f":{url.port}"
        path = url.path.rstrip("/") or "/v1"
        self.base_url = urlunsplit((url.scheme, netloc, path, "", ""))
        return self


class Endpoint(EndpointInput):
    id: UUID


class ProfileInput(Contract):
    endpoint_id: UUID
    model: str = Field(min_length=1, max_length=200)
    context_window: int = Field(default=32768, ge=512, le=2000000)
    max_output_tokens: int = Field(default=2048, ge=32, le=32768)
    temperature: float = Field(default=0.1, ge=0, le=2)
    top_p: float = Field(default=1, gt=0, le=1)
    structured_mode: Literal["json_schema", "json_object", "none"] = "json_schema"

    @model_validator(mode="after")
    def budget(self) -> Self:
        if self.max_output_tokens >= self.context_window:
            raise ValueError("Output budget must be smaller than the context window")
        return self


class Profile(ProfileInput):
    id: UUID
    custom_preference: str | None = None
    custom_digest: str | None = None


class Assignment(Contract):
    task: Task
    profile_id: UUID


class WorkspaceSettings(Contract):
    endpoints: list[Endpoint]
    profiles: list[Profile]
    assignments: list[Assignment]


class ModelList(Contract):
    models: list[str]


class ConnectionResult(Contract):
    ok: bool = Field(strict=True)


class Detection(Contract):
    name: str
    provider: Literal["lm_studio", "ollama"]
    base_url: str
    models: list[str]
    available: bool
