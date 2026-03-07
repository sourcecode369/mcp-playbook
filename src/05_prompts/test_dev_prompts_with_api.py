"""
Testing prompts with the Claude API is different from testing tools.
Prompts don't call any tools — they just build a structured message string
and send it directly to the LLM. So there's no tool loop here.

We import the prompt functions, call them to get the prompt text,
then send that text to the Claude API as a user message.
"""
import anthropic
from dotenv import load_dotenv
from pathlib import Path
from dev_prompts import code_review, write_tests, explain_error, git_commit, document_code, refactor

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

def ask(prompt_text: str, max_tokens: int = 1024) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt_text}]
    )
    return response.content[0].text


# ─── Sample code with intentional bugs ────────────────────────────────────────

BUGGY_CODE = """
def get_user(id):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id = {id}")
    return cur.fetchone()
"""

SAMPLE_FUNCTION = """
def calculate_discount(price, discount_percent):
    discounted = price - (price * discount_percent / 100)
    return discounted
"""

SAMPLE_DIFF = """
-def fetch_data(url):
-    import requests
-    r = requests.get(url)
-    return r.json()
+async def fetch_data(url: str) -> dict:
+    async with httpx.AsyncClient(timeout=10) as client:
+        r = await client.get(url)
+        r.raise_for_status()
+        return r.json()
"""

SAMPLE_ERROR = """
Traceback (most recent call last):
  File "app.py", line 12, in <module>
    result = calculate_discount(price, discount)
  File "app.py", line 5, in calculate_discount
    discounted = price - (price * discount_percent / 100)
TypeError: unsupported operand type(s) for *: 'str' and 'int'
"""

# ─── Run each prompt ───────────────────────────────────────────────────────────

tests = [
    ("code_review — security focus",
     code_review(language="python", code=BUGGY_CODE, focus="security")),

    ("write_tests — pytest",
     write_tests(language="python", code=SAMPLE_FUNCTION, framework="pytest")),

    ("explain_error",
     explain_error(error=SAMPLE_ERROR, context="Running a Flask API endpoint")),

    ("git_commit — fix type",
     git_commit(diff=SAMPLE_DIFF, commit_type="refactor")),

    ("document_code — google style",
     document_code(language="python", code=SAMPLE_FUNCTION, style="google")),

    ("refactor — readability",
     refactor(language="python", code=BUGGY_CODE, goal="readability")),
]

for name, prompt_text in tests:
    print(f"\n{'='*60}")
    print(f"PROMPT: {name}")
    print('='*60)
    result = ask(prompt_text)
    print(result[:800])
    print("..." if len(result) > 800 else "")
