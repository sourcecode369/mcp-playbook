"""
Testing long_running_server.py with the Claude API.

All three tools use ctx: Context so we can't import and call them directly.
We simulate the logic inline — same outputs, no ctx dependency.

Note: Progress notifications and MCP logging (ctx.info, ctx.warning, ctx.error)
only work through a real MCP connection (Claude Desktop or Chapter 11 client).
Here we simulate the final results and show Claude reasoning about them.
"""
import anthropic, json, asyncio, random, os
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

tools = [
    {
        "name": "scan_directory",
        "description": "Simulate scanning a directory tree with progress updates. Reports file and directory counts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to scan"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "simulate_training",
        "description": "Simulate an ML training run with per-epoch progress and metrics. epochs: 1-20.",
        "input_schema": {
            "type": "object",
            "properties": {
                "epochs": {"type": "integer", "description": "Number of training epochs (1-20)"}
            },
            "required": ["epochs"]
        }
    },
    {
        "name": "progress_batch",
        "description": "Process a batch of items with some failing. batch_size: 1-50, fail_rate: 0.0-1.0.",
        "input_schema": {
            "type": "object",
            "properties": {
                "batch_size": {"type": "integer", "description": "Number of items to process (1-50)"},
                "fail_rate": {"type": "number", "description": "Fraction of items that fail (0.0-1.0)"}
            },
            "required": ["batch_size", "fail_rate"]
        }
    }
]

def run_scan_directory(path: str) -> str:
    if not os.path.exists(path):
        return f"Directory not found: {path}"
    files, dirs = [], []
    for root, subdirs, filenames in os.walk(path):
        files.extend(filenames)
        dirs.append(root)
    return json.dumps({
        "path": path,
        "total_directories": len(dirs),
        "total_files": len(files),
        "scan_time": datetime.now().isoformat()
    }, indent=2)

def run_simulate_training(epochs: int) -> str:
    epochs = max(1, min(20, epochs))
    log = []
    for epoch in range(1, epochs + 1):
        loss = round(1.0 / (epoch * 0.5 + 0.1) + random.uniform(-0.05, 0.05), 4)
        acc = round(1.0 - loss * 0.5, 4)
        log.append({"epoch": epoch, "loss": loss, "accuracy": acc})
    best = min(log, key=lambda x: x["loss"])
    return json.dumps({
        "epochs_run": epochs,
        "final_loss": log[-1]["loss"],
        "best_epoch": best,
        "history": log
    }, indent=2)

def run_progress_batch(batch_size: int, fail_rate: float) -> str:
    batch_size = max(1, min(50, batch_size))
    fail_rate = max(0.0, min(1.0, fail_rate))
    succeeded, failed = 0, 0
    for _ in range(batch_size):
        if random.random() < fail_rate:
            failed += 1
        else:
            succeeded += 1
    return json.dumps({
        "total": batch_size,
        "succeeded": succeeded,
        "failed": failed,
        "success_rate": f"{succeeded / batch_size:.0%}"
    })

def run_tool(name: str, args: dict) -> str:
    if name == "scan_directory":    return run_scan_directory(**args)
    if name == "simulate_training": return run_simulate_training(**args)
    if name == "progress_batch":    return run_progress_batch(**args)
    return f"Unknown tool: {name}"

def chat_with_tools(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Tool called: {block.name}\t({block.input})")
                    result = run_tool(block.name, block.input)
                    print(f"  Result: {str(result)[:150]}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": results})
        else:
            return response.content[0].text


queries = [
    "Scan the /tmp directory and tell me how many files and folders it contains.",
    "Train a model for 8 epochs and tell me which epoch had the best loss and what it was.",
    "Process a batch of 20 items with a 30% fail rate. Is that acceptable or too high?",
    # Multi-tool: Claude will call training then batch to compare
    "Run a 5-epoch training and a 10-item batch with 10% fail rate. Summarize both results.",
]

for q in queries:
    print(f"\n{'='*55}\nQ: {q}\n{'='*55}")
    print(chat_with_tools(q))
