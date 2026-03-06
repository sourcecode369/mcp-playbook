from fastmcp import FastMCP
import os, platform, subprocess, time
from datetime import datetime
from typing import Literal 

mcp = FastMCP("system-monitor")

@mcp.tool()
def get_system_info() -> dict:
    """
        Get OS, Python version, hostname, architecture and uptime.
    """
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "hostname": platform.node(),
        "python": platform.python_version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "timestamp": datetime.now().isoformat()
    }
    
@mcp.tool()
def get_disk_usage(path: str="/") -> dict:
    """
        Get disk usage statistics for a given path.
        Returns total, used, free in GB and usage perecentage.
    """
    
    stat = os.statvfs(path)
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bfree * stat.f_frsize
    used = total - free
    return {
        "path": path,
        "total_gb": round(total / 1024 ** 3, 2),
        "used_gb": round(used / 1024**3, 2),
        "free_gb": round(free / 1024**3, 2),
        "percent_used": round((used / total) * 100, 1),
    }
    
@mcp.tool()
def get_cpu_and_memory() -> dict:
    """
    Get CPU and RAM usage. Requires psutil (pip install psutil).
    Returns percentages and raw values.
    """
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": cpu,
            "cpu_cores": psutil.cpu_count(),
            "ram_total_mb": round(mem.total / 1024**2),
            "ram_used_mb": round(mem.used / 1024**2),
            "ram_percent": mem.percent,
        }
    except ImportError:
        return {"error": "psutil not installed. Run: pip install psutil"}
    
@mcp.tool()
def list_processes(sort_by: Literal["cpu", "memory", "name"] = "cpu", limit: int = 10) -> str:
    """
    List running processes sorted by CPU, memory, or name.
    Returns a formatted table.
    """
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except Exception:
                pass

        key = {"cpu": "cpu_percent", "memory": "memory_percent", "name": "name"}[sort_by]
        reverse = sort_by != "name"
        procs = sorted(procs, key=lambda x: x.get(key) or 0, reverse=reverse)[:limit]

        lines = [f"{'PID':<8}{'CPU%':<8}{'MEM%':<8}NAME"]
        for p in procs:
            lines.append(f"{p['pid']:<8}{p['cpu_percent'] or 0:<8.1f}{p['memory_percent'] or 0:<8.1f}{p['name']}")
        return "\n".join(lines)
    except ImportError:
        return "psutil not installed. Run: pip install psutil"
    
@mcp.tool()
def run_safe_command(command: Literal["ls", "pwd", "date", "whoami", "uname", "uptime", "df", "env"]) -> str:
    """
    Run a safe read-only shell command. Only a fixed allowlist is permitted.
    Returns stdout output.
    """
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
    return result.stdout.strip() or result.stderr.strip()

if __name__ == "__main__":
    mcp.run()