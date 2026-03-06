# Chapter 9 — Real Project: GitHub Server

## Setup

```bash
pip install httpx python-dotenv
echo "GITHUB_TOKEN=ghp_your_token_here" >> .env
```

Get a token at github.com/settings/tokens — needs `repo` and `read:user` scopes.

---

## Full GitHub MCP Server

```python
# chapter09/github_server.py
from fastmcp import FastMCP
import httpx, os, base64, json
from dotenv import load_dotenv
from typing import Literal

load_dotenv()
TOKEN = os.getenv("GITHUB_TOKEN")
BASE = "https://api.github.com"

mcp = FastMCP("github")

def headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

async def gh_get(path: str, params: dict = None) -> dict | list:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{BASE}{path}", headers=headers(), params=params or {})
        r.raise_for_status()
        return r.json()

async def gh_post(path: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{BASE}{path}", headers=headers(), json=data)
        r.raise_for_status()
        return r.json()

async def gh_patch(path: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.patch(f"{BASE}{path}", headers=headers(), json=data)
        r.raise_for_status()
        return r.json()

# ─── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_repos(username: str, type: Literal["all", "owner", "member"] = "owner", limit: int = 10) -> str:
    """List repositories for a GitHub user or organization."""
    data = await gh_get(f"/users/{username}/repos", {"type": type, "per_page": min(limit, 30)})
    lines = [f"• {r['full_name']} — ⭐{r['stargazers_count']} | {r.get('language','N/A')} | {r['description'] or ''}"
             for r in data[:limit]]
    return "\n".join(lines) or "No repositories found."

@mcp.tool()
async def get_repo(owner: str, repo: str) -> str:
    """Get detailed information about a specific repository."""
    r = await gh_get(f"/repos/{owner}/{repo}")
    return (f"**{r['full_name']}**\n"
            f"Description: {r['description']}\n"
            f"Stars: {r['stargazers_count']} | Forks: {r['forks_count']} | Issues: {r['open_issues_count']}\n"
            f"Language: {r['language']} | License: {(r.get('license') or {}).get('name', 'None')}\n"
            f"Created: {r['created_at'][:10]} | Updated: {r['updated_at'][:10]}\n"
            f"URL: {r['html_url']}")

@mcp.tool()
async def list_issues(owner: str, repo: str,
                      state: Literal["open", "closed", "all"] = "open",
                      limit: int = 10) -> str:
    """List issues in a repository."""
    data = await gh_get(f"/repos/{owner}/{repo}/issues",
                        {"state": state, "per_page": min(limit, 30)})
    issues = [f"#{i['number']} [{i['state']}] {i['title']} — @{i['user']['login']}"
              for i in data if "pull_request" not in i]
    return "\n".join(issues[:limit]) or "No issues found."

@mcp.tool()
async def create_issue(owner: str, repo: str, title: str,
                       body: str = "", labels: list[str] = None) -> str:
    """Create a new issue in a repository."""
    r = await gh_post(f"/repos/{owner}/{repo}/issues",
                      {"title": title, "body": body, "labels": labels or []})
    return f"Created issue #{r['number']}: {r['html_url']}"

@mcp.tool()
async def close_issue(owner: str, repo: str, number: int) -> str:
    """Close an open issue by number."""
    r = await gh_patch(f"/repos/{owner}/{repo}/issues/{number}", {"state": "closed"})
    return f"Closed issue #{r['number']}: {r['html_url']}"

@mcp.tool()
async def get_file(owner: str, repo: str, path: str, branch: str = "main") -> str:
    """Read the contents of a file in a repository."""
    data = await gh_get(f"/repos/{owner}/{repo}/contents/{path}", {"ref": branch})
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content

@mcp.tool()
async def list_pull_requests(owner: str, repo: str,
                              state: Literal["open", "closed", "all"] = "open",
                              limit: int = 10) -> str:
    """List pull requests in a repository."""
    data = await gh_get(f"/repos/{owner}/{repo}/pulls",
                        {"state": state, "per_page": min(limit, 30)})
    prs = [f"#{p['number']} {p['title']} — @{p['user']['login']} ({p['head']['ref']}→{p['base']['ref']})"
           for p in data[:limit]]
    return "\n".join(prs) or "No pull requests found."

@mcp.tool()
async def get_commit_history(owner: str, repo: str,
                              branch: str = "main", limit: int = 10) -> str:
    """Get recent commit history for a repository."""
    data = await gh_get(f"/repos/{owner}/{repo}/commits",
                        {"sha": branch, "per_page": min(limit, 30)})
    lines = [f"{c['sha'][:7]} {c['commit']['message'].splitlines()[0]} — {c['commit']['author']['name']}"
             for c in data[:limit]]
    return "\n".join(lines)

@mcp.tool()
async def search_code(query: str, language: str = "", limit: int = 5) -> str:
    """Search for code across GitHub repositories."""
    q = f"{query} language:{language}" if language else query
    data = await gh_get("/search/code", {"q": q, "per_page": min(limit, 10)})
    results = [f"• {i['repository']['full_name']}/{i['path']}"
               for i in data.get("items", [])[:limit]]
    return "\n".join(results) or "No results found."

@mcp.tool()
async def get_user_info(username: str) -> str:
    """Get public profile information for a GitHub user."""
    u = await gh_get(f"/users/{username}")
    return (f"Login: {u['login']} | Name: {u.get('name', 'N/A')}\n"
            f"Bio: {u.get('bio', 'N/A')}\n"
            f"Repos: {u['public_repos']} | Followers: {u['followers']} | Following: {u['following']}\n"
            f"URL: {u['html_url']}")

# ─── Resources ────────────────────────────────────────────────────────────────

@mcp.resource("github://user/me")
async def my_profile() -> str:
    """Authenticated user's GitHub profile."""
    try:
        u = await gh_get("/user")
        return json.dumps(u, indent=2)
    except Exception as e:
        return f"Error: {e}"

@mcp.resource("github://repos/{owner}/{repo}")
async def repo_info(owner: str, repo: str) -> str:
    """Repository information as a resource."""
    data = await gh_get(f"/repos/{owner}/{repo}")
    return json.dumps(data, indent=2)

@mcp.resource("github://repos/{owner}/{repo}/issues/{number}")
async def issue_detail(owner: str, repo: str, number: str) -> str:
    """Detailed information about a specific issue."""
    data = await gh_get(f"/repos/{owner}/{repo}/issues/{number}")
    return json.dumps(data, indent=2)

if __name__ == "__main__":
    mcp.run()
```

---

## Claude API Test

```python
# chapter09/test_github_api.py
from anthropic import Anthropic
import asyncio, json
from dotenv import load_dotenv
import sys; sys.path.insert(0, ".")
from github_server import list_repos, get_repo, list_issues, search_code

load_dotenv()
client = Anthropic()

tools = [
    {"name": "list_repos",
     "description": "List repositories for a GitHub user.",
     "input_schema": {"type": "object", "properties": {
         "username": {"type": "string"},
         "limit": {"type": "integer", "default": 5}
     }, "required": ["username"]}},
    {"name": "get_repo",
     "description": "Get detailed info about a repository.",
     "input_schema": {"type": "object", "properties": {
         "owner": {"type": "string"}, "repo": {"type": "string"}
     }, "required": ["owner", "repo"]}},
    {"name": "search_code",
     "description": "Search for code across GitHub.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string"}, "language": {"type": "string"}
     }, "required": ["query"]}},
]

def execute(name, args):
    return asyncio.run({
        "list_repos": lambda: list_repos(**args),
        "get_repo": lambda: get_repo(**args),
        "search_code": lambda: search_code(**args),
    }[name]())

queries = [
    "List the top 5 repos for the 'anthropics' GitHub organization",
    "Search for Python code that uses the MCP protocol",
    "Get details about the anthropics/anthropic-sdk-python repo",
]

for query in queries:
    print(f"\n{'='*50}\nQuery: {query}\n{'='*50}")
    messages = [{"role": "user", "content": query}]
    while True:
        resp = client.messages.create(model="claude-opus-4-6", max_tokens=512, tools=tools, messages=messages)
        if resp.stop_reason != "tool_use":
            print(resp.content[0].text)
            break
        messages.append({"role": "assistant", "content": resp.content})
        results = [{"type": "tool_result", "tool_use_id": b.id, "content": execute(b.name, b.input)}
                   for b in resp.content if b.type == "tool_use"]
        messages.append({"role": "user", "content": results})
```

**Claude Desktop tests:**
1. *"List my GitHub repositories"*
2. *"Create an issue titled 'Test from MCP' in [your-username]/[your-repo]"*
3. *"What are the latest commits on the main branch of [owner]/[repo]?"*
4. *"Search GitHub for Python files that use asyncio"*
