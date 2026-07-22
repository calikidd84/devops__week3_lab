import json
import os
import re

from github import Github
from openai import OpenAI


SYSTEM_PROMPT = """You are a build-fixer agent. Your only job is to identify
the root cause of a failing Python test and propose the minimal fix to the
source file. Change exactly one file: the source file under test, never the
test file. Return JSON only with these keys: root_cause, fix_description,
fixed_file_path, fixed_file_content. Do not include Markdown."""


def _extract_json(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def propose_fix(build_log, source_code):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )

    response = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "openrouter/free"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Build log:\n```\n{build_log}\n```\n\n"
                    f"Source file (src/calculator.py):\n```python\n{source_code}\n```"
                ),
            },
        ],
    )

    content = response.choices[0].message.content
    fix = _extract_json(content)

    required = {
        "root_cause",
        "fix_description",
        "fixed_file_path",
        "fixed_file_content",
    }
    missing = required - set(fix)
    if missing:
        raise ValueError(f"Agent response missing required keys: {sorted(missing)}")
    if fix["fixed_file_path"] != "src/calculator.py":
        raise ValueError("Agent tried to edit a file outside the allowed target")

    return fix


def open_pr(fix):
    gh = Github(os.environ["GH_TOKEN"])
    repo = gh.get_repo(os.environ["REPO"])
    base = os.environ.get("BASE_BRANCH", "main")
    branch_name = f"bot/fix-build-{os.environ.get('GITHUB_RUN_ID', 'local')}"

    base_ref = repo.get_git_ref(f"heads/{base}")
    repo.create_git_ref(f"refs/heads/{branch_name}", base_ref.object.sha)

    contents = repo.get_contents(fix["fixed_file_path"], ref=base)
    repo.update_file(
        fix["fixed_file_path"],
        f"[bot] fix: {fix['root_cause'][:72]}",
        fix["fixed_file_content"],
        contents.sha,
        branch=branch_name,
    )

    pr = repo.create_pull(
        title=f"[Bot Fix] {fix['root_cause'][:60]}",
        body=(
            "## Agent-Proposed Fix\n\n"
            f"**Root cause:** {fix['root_cause']}\n\n"
            f"**Change:** {fix['fix_description']}\n\n"
            "---\n"
            "This PR was opened by the build-fixer agent. "
            "A human must review and approve before merging.\n\n"
            "**Checklist before approving:**\n"
            "- [ ] The proposed fix matches the described root cause\n"
            "- [ ] No unrelated changes are included\n"
            "- [ ] The fix does not touch infrastructure or deployment files\n"
        ),
        head=branch_name,
        base=base,
    )
    print(f"Opened PR #{pr.number}: {pr.html_url}")


def run():
    with open("build_log.txt", encoding="utf-8") as f:
        build_log = f.read()

    with open("src/calculator.py", encoding="utf-8") as f:
        source_code = f.read()

    fix = propose_fix(build_log, source_code)
    print(f"Agent identified root cause: {fix['root_cause']}")
    print(f"Agent proposed change: {fix['fix_description']}")
    open_pr(fix)


if __name__ == "__main__":
    run()
