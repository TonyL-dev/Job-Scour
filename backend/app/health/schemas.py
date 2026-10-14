from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    service: str
    version: str
    mode: Literal["local", "server"]
    database: Literal["ready", "unavailable"]


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
