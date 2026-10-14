import re

from fastapi import HTTPException

from app.ai.gateway import Gateway, Progress
from app.ai.prompts import messages, validate_evidence
from app.jobs.schemas import JobAnalysis, PromptInfo, Requirement
from app.settings.schemas import Endpoint, Profile

EXTRACTION_VERSION = "2.1"


def explicit_metadata(analysis: JobAnalysis, text: str) -> JobAnalysis:
    # Only explicit title/requirement syntax; never company age or inferred seniority.
    level = re.match(
        r"(?i)^(?:job title:\s*)?"
        r"(?P<level>senior|junior|lead|principal|staff|entry[- ]level|mid[- ]level)"
        r"\s+(?:[a-z-]+\s+){0,3}"
        r"(?:engineer|developer|analyst|designer|manager|architect|scientist|specialist|consultant)"
        r"\s*(?:[.\n(]|$)",
        text,
    )
    years = re.search(
        r"(?i)\b(?:required|minimum)\s+experience\s*:\s*"
        r"(?P<years>\d{1,2}(?:\s*[-–]\s*\d{1,2})?\+?\s+years?)\b",
        text,
    )
    updates = {}
    if level:
        quote = level.group("level")
        updates["seniority"] = Requirement(term=quote, evidence=quote)
    if years:
        quote = years.group("years")
        updates["years_experience"] = Requirement(term=quote, evidence=quote)
    return analysis.model_copy(update=updates)


async def analyze_job(
    gateway: Gateway,
    endpoint: Endpoint,
    profile: Profile,
    text: str,
    prompt: PromptInfo,
    progress: Progress | None = None,
) -> JobAnalysis:
    system, user = messages(text, prompt, profile.structured_mode != "json_schema")
    for attempt in range(2):
        analysis = await gateway.structured(endpoint, profile, system, user, JobAnalysis, progress)
        try:
            validate_evidence(analysis, text)
            return explicit_metadata(analysis, text)
        except ValueError as error:
            if attempt:
                raise HTTPException(
                    502, "Model evidence did not quote the job description. No analysis was saved."
                ) from error
            user += (
                "\nCorrect evidence quotes. Every evidence value must be an EXACT substring "
                "of the actual description. Copy named skills verbatim as evidence. "
                "Do not explain or paraphrase evidence."
            )
    raise AssertionError("Unreachable")
