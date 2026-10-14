from typing import Literal
from uuid import UUID

from pydantic import Field

from app.career.schemas import Contract
from app.resumes.schemas import StyleOverrides
from app.resumes.schemas import TemplateSnapshot as TemplateSnapshot


class TemplateSave(Contract):
    name: str = Field(min_length=1, max_length=120)
    base: Literal["classic", "modern"] = "classic"
    html: str = Field(default="{{header}}{{sections}}", max_length=16000)
    css: str = Field(default="", max_length=4000)
    styles: StyleOverrides = Field(default_factory=StyleOverrides)
    asset_ids: list[UUID] = Field(default_factory=list, max_length=4)
    expected_revision: int = Field(default=0, ge=0)


class CustomTemplate(Contract):
    id: UUID
    document_id: UUID
    revision: int
    retired: bool
    snapshot: TemplateSnapshot


class AssetUpload(Contract):
    content_base64: str = Field(max_length=350000)


class Asset(Contract):
    id: UUID
    width: int
    height: int
