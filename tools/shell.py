from __future__ import annotations

import subprocess

ALLOWED_COMMANDS = [
    "ls",
    "pwd",
    "whoami",
    "date",
    "uname",
]


def run_shell_command(command: str) -> str:
    try:
        cmd = command.split()[0]
        if cmd not in ALLOWED_COMMANDS:
            return "BLOCKED: Command not allowed"

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"ERROR: {str(e)}"
