"""Register the complete portable model catalogue for offline storage validation."""

from importlib import import_module


def register_models() -> None:
    for domain in (
        "auth",
        "career",
        "resumes",
        "settings",
        "ai",
        "jobs",
        "ats",
        "applications",
        "importers",
        "profile",
        "cover_letters",
        "prompt_management",
        "templates",
    ):
        import_module(f"app.{domain}.models")
    import_module("app.resumes.generation_models")
