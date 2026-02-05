import sys
import traceback
from types import SimpleNamespace
from rich import print as rprint
from rich.panel import Panel
from rich.console import Group
from rich.traceback import Traceback

def handle_error(ctx: str, e: Exception, opts: SimpleNamespace, critical: bool = False) -> bool:
    """
    Log error with rich Panel (ctx + e + TB if debug), raise if debug/critical else return False.

    Args:
        ctx: Context string (e.g., "exec_module foo.py").
        e: Caught exception.
        opts: Global opts (debug flag).
        critical: Fail-fast even non-debug.

    Returns:
        bool: False (for continue/skip).
    """
    import traceback
    from rich.panel import Panel
    from rich import print as rprint

    tb_str = traceback.format_exc() if getattr(opts, 'debug', False) else ''
    msg_lines = [
        f"[bold red]{type(e).__name__}: {str(e)}",
        f"[italic yellow]{ctx}"
    ]
    if tb_str.strip():
        msg_lines.append(f"[bright_red]Traceback:[/]\n[red]{tb_str.strip()}[/]")

    panel = Panel('\n'.join(msg_lines), title="[bold red]Error[/]", border_style="red")
    rprint(panel)

    if getattr(opts, 'debug', False) or critical:
        raise
    return False