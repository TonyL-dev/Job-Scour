from pydantic import Field

from app.career.schemas import Contract


class PasscodeInput(Contract):
    passcode: str = Field(min_length=8, max_length=128)
    current_passcode: str | None = Field(default=None, max_length=128)


class UnlockInput(Contract):
    passcode: str = Field(min_length=1, max_length=128)


class PrivacyStatus(Contract):
    passcode_enabled: bool
    locked: bool
    encryption_enabled: bool
    database_encrypted: bool = False
    encryption_scope: str = (
        "Descriptive career/job/tracker text and JSON snapshots. IDs, dates, numeric fields, "
        "statuses and indexes remain queryable. Exports and downloaded PDFs are plaintext."
    )


class DeleteInput(Contract):
    confirmation: str
