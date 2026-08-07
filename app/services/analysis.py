"""AI-powered analysis of GitHub repositories, issues, and pull requests.

These helpers build focused prompts from a bounded slice of repository context
and delegate to the configured LLM provider. The prompts ask the model to
clearly label uncertainty so the UI can distinguish confirmed defects from
suggestions.
"""

from __future__ import annotations

from app.services.llm import LLMProviderError, get_provider

# Hard cap on the amount of repository text fed to the model for any single
# analysis, so a request never uploads the whole repository.
MAX_CONTEXT_CHARS = 40_000

_SYSTEM = (
    "You are an expert software engineering analyst. Be concrete, cite the "
    "specific code you refer to, and be honest about uncertainty. Clearly "
    "label every finding: prefix confirmed defects or facts with "
    "'[CONFIRMED]' and anything that is a hypothesis, trade-off, or suggestion "
    "with '[SUGGESTION]'."
)


def _run(prompt: str, *, system: str = _SYSTEM) -> str:
    """Run a single completion with the configured provider."""
    try:
        provider = get_provider()
        return provider.complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        )
    except LLMProviderError as exc:
        return f"[analysis unavailable: {exc}]"


def _clip(text: str, limit: int = MAX_CONTEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…[context truncated]"


def analyze_issue(issue: dict, owner: str, repo: str) -> dict:
    """Produce a structured AI analysis of a GitHub issue."""
    body = issue.get("body") or "(no description provided)"
    labels = ", ".join(issue.get("labels") or []) or "none"
    prompt = f"""Repository: {owner}/{repo}
Issue #{issue.get('number')}: {issue.get('title')}
State: {issue.get('state')}
Labels: {labels}

Description:
{_clip(body)}

Provide a structured analysis with these sections:
1. Summary - one short paragraph
2. Problem identification - what is actually being asked/fixed
3. Suggested implementation approach - concrete steps
4. Suggested acceptance criteria - bullet list, testable
5. Complexity/difficulty estimation - easy/medium/hard with one-line reasoning
"""
    return {
        "kind": "issue",
        "issue_number": issue.get("number"),
        "title": issue.get("title"),
        "analysis": _run(prompt),
    }


def analyze_pull_request(pr: dict, files: list[dict]) -> dict:
    """Produce a structured AI analysis of a pull request."""
    body = pr.get("body") or "(no description provided)"
    changed = []
    for file in files[:40]:
        patch = file.get("patch") or ""
        changed.append(
            f"- {file.get('filename')} ({file.get('status')}, "
            f"+{file.get('additions')}/-{file.get('deletions')})\n"
            f"{_clip(patch, 6000)}"
        )
    files_text = "\n".join(changed) if changed else "(no file-level diff available)"

    prompt = f"""Pull request #{pr.get('number')}: {pr.get('title')}
State: {pr.get('state')} (merged: {pr.get('merged')})
Author: {pr.get('author')}
Base: {pr.get('base')} -> Head: {pr.get('head')}

Description:
{_clip(body)}

Changed files:
{_clip(files_text, MAX_CONTEXT_CHARS // 2)}

Provide a structured review with these sections:
1. Summary - what this PR does, one short paragraph
2. Code-change explanation - what each notable change does
3. Potential bugs - clearly mark [CONFIRMED] vs [SUGGESTION]
4. Suggested tests - concrete test cases for the new behaviour
5. Review checklist - bullet list of things to verify before merge
"""
    return {
        "kind": "pull_request",
        "pr_number": pr.get("number"),
        "title": pr.get("title"),
        "analysis": _run(prompt),
    }


def analyze_file(filename: str, language: str, code: str, question: str | None = None) -> dict:
    """Analyze a single file's contents (explain, find problems, etc.)."""
    if question:
        prompt = (
            f"File: {filename} (language: {language})\n\n"
            f"Code:\n{_clip(code)}\n\n"
            f"Question: {question}\n"
            "Answer the question directly, referencing specific lines where possible."
        )
    else:
        prompt = (
            f"File: {filename} (language: {language})\n\n"
            f"Code:\n{_clip(code)}\n\n"
            "Review this file: briefly explain its purpose, then identify potential "
            "bugs or problems. Mark [CONFIRMED] for definite defects and [SUGGESTION] "
            "for possible issues or improvements."
        )
    return {"kind": "file", "filename": filename, "analysis": _run(prompt)}


def summarize_repository(owner: str, repo: str, readme: str | None, file_list: list[str]) -> dict:
    """Produce a short overview of a repository from README + file list."""
    prompt = (
        f"Repository: {owner}/{repo}\n\n"
        f"README:\n{_clip(readme or '(no README available)', 20000)}\n\n"
        f"Top-level structure (sample):\n{_clip('\n'.join(file_list[:300]), 15000)}\n\n"
        "Explain in 2-4 sentences what this repository does, its main components, "
        "and the primary technologies used."
    )
    return {"kind": "repository", "full_name": f"{owner}/{repo}", "analysis": _run(prompt)}
