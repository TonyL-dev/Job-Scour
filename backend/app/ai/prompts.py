import hashlib
import json
from importlib.resources import files

from app.jobs.schemas import JobAnalysis, PromptInfo


def job_prompt() -> PromptInfo:
    raw = files("app.ai").joinpath("prompts/job_analysis.v2.json").read_text(encoding="utf-8")
    return PromptInfo(**json.loads(raw), digest=hashlib.sha256(raw.encode()).hexdigest())


def messages(text: str, prompt: PromptInfo, include_schema: bool = True) -> tuple[str, str]:
    schema = (
        json.dumps(JobAnalysis.model_json_schema())
        if include_schema
        else "Use the response_format schema. Extract required_skills, preferred_skills, "
        "technologies, responsibilities, company_values, industry_terms, keywords, seniority, "
        "years_experience. Each list item has term and evidence; keywords also have weight."
    )
    return prompt.system_text, prompt.user_template.format(schema=schema, job=json.dumps(text))


def validate_evidence(analysis: JobAnalysis, text: str) -> None:
    for collection in (
        analysis.required_skills,
        analysis.preferred_skills,
        analysis.technologies,
        analysis.responsibilities,
        analysis.company_values,
        analysis.industry_terms,
        analysis.keywords,
        [analysis.seniority, analysis.years_experience],
    ):
        for requirement in collection:
            if requirement is not None and requirement.evidence not in text:
                raise ValueError("Analysis evidence must quote the job description exactly")
