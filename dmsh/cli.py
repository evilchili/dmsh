import asyncio
import sys
import termios

import typer

from dmsh.shell.interactive_shell import DMShell

CONFIG = {
    # where to find campaign data
    "data_path": '~/.dnd',
    "campaign_name": "deadsands",

    # campaign start date
    "campaign_start_date": "2.1125.5.25",
}


app = typer.Typer()


@app.callback(invoke_without_command=True)
def dmsh():
    old_attrs = termios.tcgetattr(sys.stdin)
    try:
        asyncio.run(DMShell(CONFIG).start())
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSANOW, old_attrs)


if __name__ == "__main__":
    app.main()
