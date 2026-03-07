from fastmcp import FastMCP

mcp = FastMCP("dev-prompts")

@mcp.prompt()
def code_review(
    language: str,
    code: str,
    focus: str = "all"
) -> str:
    """
        Comprehensive code review: correctness, security, performance, style. 
        focus: security | performance | reliability | all
    """
    
    return f"""
    Review this {language} code. Focus on {focus}.
    For each issue found: 
    1. Identify the exact line / section
    2. Explain the problem directly
    3. Provide corrected code
    
    After all issues, give a quality score (1-10) and a one-paragraph summary

    ```
        {language}
        {code}
    ```
"""

@mcp.prompt()
def write_tests(
    language: str,
    code: str,
    framework: str = "pytest"
) -> str:
    """
    Generate thorough unit tests with edge cases and error paths.
    """
    return f"""Write comprehensive {framework} tests for this {language} code.

    Cover:
    - Happy paths (normal expected usage)
    - Edge cases (empty inputs, boundary values, None/null)
    - Error cases (invalid inputs, exceptions that should be raised)

    Each test must have a descriptive name explaining what it verifies.
    Add a brief comment per test explaining the scenario.

    ```{language}
    {code}
    ```"""

@mcp.prompt()
def explain_error(error: str, context: str = "") -> str:
    """
    Explain an error message and provide a step-by-step fix.
    Paste the full traceback as 'error'.
    """
    ctx_section = f"\nContext: {context}" if context else ""
    return f"""Explain this error and how to fix it.{ctx_section}

    Error/Traceback:
    ```
    {error}
    ```

    Provide:
    1. Plain-English explanation of what this error means
    2. Most likely root cause(s)
    3. Step-by-step fix instructions
    4. Corrected code if applicable
    5. How to prevent this error in future
    """
    
@mcp.prompt()
def git_commit(diff: str, commit_type: str = "") -> str:
    """
    Generate a Conventional Commits message from a git diff.
    commit_type: feat | fix | refactor | docs | test | chore
    """
    type_hint = f"The commit type should be: {commit_type}" if commit_type else "Choose the appropriate Conventional Commits type."
    return f"""Generate a git commit message for this diff.

    {type_hint}
    Format: <type>(<optional scope>): <short description>
    Body: explain WHY (not what) if the change is non-trivial.

    Diff:
    ```diff
    {diff}
    ```"""

@mcp.prompt()
def document_code(language: str, code: str, style: str = "google") -> str:
    """
    Generate documentation for code.
    style: google | numpy | sphinx | plain
    """
    return f"""Generate {style}-style documentation for this {language} code.

Include:
- Module/file level docstring
- Function/method docstrings with params, returns, raises, and a usage example
- Class docstrings with attribute descriptions
- Inline comments only for non-obvious logic

Return the fully documented code.

```{language}
{code}
```"""

@mcp.prompt()
def refactor(language: str, code: str, goal: str = "readability") -> str:
    """
    Suggest and apply refactoring improvements.
    goal: readability | performance | maintainability | all
    """
    return f"""Refactor this {language} code to improve {goal}.

Provide:
1. Summary of what's wrong with the current code
2. The refactored code with comments explaining each significant change
3. A before/after comparison table of key improvements

```{language}
{code}
```"""

@mcp.prompt()
def architecture_review(
    description: str,
    tech_stack: str = "",
    concerns: str = ""
) -> str:
    """
    Review a system architecture or design proposal.
    Provide a description of what you're building.
    """
    stack_section = f"\nTech stack: {tech_stack}" if tech_stack else ""
    concern_section = f"\nSpecific concerns: {concerns}" if concerns else ""
    return f"""Review this system architecture proposal.{stack_section}{concern_section}

Description:
{description}

Evaluate:
1. Scalability — will it handle 10x the expected load?
2. Reliability — single points of failure, fault tolerance
3. Security — attack surface, data exposure risks
4. Maintainability — complexity, team onboarding cost
5. Cost — estimated infrastructure cost at scale

For each: rate 1-5 and explain. End with your top 3 recommendations."""

if __name__ == "__main__":
    mcp.run()