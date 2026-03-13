from fastmcp import FastMCP
from mcp.server.fastmcp import Context
import asyncio, random, json
from datetime import datetime

mcp = FastMCP("long-running-tasks")

@mcp.tool()
async def scan_directory(path: str, ctx: Context):
    """
    Simulate scanning a directory. tree with progress updates.
    Reports each sybdirectory as its scanned.
    """
    import os
    await ctx.info(f"Scanning directory main: {path}")
    
    if not os.path.exists(path):
        await ctx.warning(f"Path does not exists: {path}")
        return f"Directory not found: {path}"
    
    files = []
    dirs = []
    all_items = list(os.walk(path))
    total = len(all_items)
    
    for i, (root, subdirs, filenames) in enumerate(all_items, 1):
        await asyncio.sleep(0.1)
        files.extend(filenames)
        dirs.append(root)
        await ctx.report_progress(progress=i, total=total)
        
        if i%5 == 0:
            await ctx.debug(f"Scanned {i}/{total} directories, {len(files)} files so far.")
    
    await ctx.info(f"Scan complete: {len(dirs)} dirs, {len(files)} files")
    return json.dumps({
        "path":path,
        "total_directories": len(dirs),
        "total_files": len(files),
        "scan_time": datetime.now().isoformat()
    }, indent=2)
    
@mcp.tool()
async def simulate_training(
    epochs: int, 
    ctx: Context
) -> str:
    """
        Simulate an ML Training run with per-epoch progress and metrics.
        epochs: number of training epochs (1-20)
    """
    
    epochs = max(1, min(20, epochs))
    await ctx.info(f"Starting training {epochs} epochs.")
    
    log = []
    for epoch in range(1, epochs+1):
        await asyncio.sleep(0.5)
        
        loss = round(1 / (epoch * 0.5 + 0.1) + random.uniform(-0.05, 0.05), 4)
        acc = round(1.0 - loss * 0.5, 4)
        log.append({"epoch": epoch, "loss": loss, "accuracy": acc})
        
        await ctx.report_progress(progress=epoch, total=epochs)
        await ctx.info(f" Epoch {epoch}/{epochs}, Loss: {loss}, Accuracy: {acc}")
        
        if loss > 1.5:
            await ctx.warning(f"High loss at epoch {epoch}: {loss:.4f}")
    
    best = min(log, key=lambda x: x["loss"])
    await ctx.info(f"Training completed. Best epoch: {best['epoch']} (loss={best['loss']:.4f})")
    return json.dumps({
        "epochs_run": epochs, "final_loss": log[-1]["loss"], "best_epoch": best, "history": log
    }, indent=2)
    
@mcp.tool()
async def progress_batch(
    batch_size: int,
    fail_rate:float,
    ctx: Context
) -> str:
    """
        Process a batch of items, with some items failing.
        batch_size: number of items (1-50)
        fail_rate: funtion of items that fail (0.0 - 1.0)
    """
    
    batch_size = max(1.0, min(50, batch_size))
    fail_rate = max(0.0, min(1.0, fail_rate))
    
    await ctx.info(f"Processing batch of {batch_size} items (fail rate: {fail_rate:.0%})")

    succeeded, failed = 0, 0
    for i in range(1, batch_size + 1):
        await asyncio.sleep(0.1)
        if random.random() < fail_rate:
            failed += 1
            await ctx.warning(f" Item {i} failed.")
        else:
            succeeded += 1
            
        await ctx.report_progress(progress=i, total=batch_size)
        
    level = "info" if failed == 0 else "warning" if failed < batch_size // 2 else "error"
    msg = f"Batch done: {succeeded} succeeded, {failed} failed"
    if level == "info": await ctx.info(msg)
    elif level == "warning": await ctx.warning(msg)
    else: await ctx.error(msg)
    
    return json.dumps({
        "total": batch_size, "succeeded": succeeded,
        "failed": failed, "success_rate": f"{succeeded / batch_size:.0%}"
    })

if __name__ == "__main__":
    mcp.run()