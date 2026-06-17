from typing import Any

class SuiCTFSandboxError(Exception):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.details = details or {}
        super().__init__(message)

    def message(self) -> str:
        return "\n".join([
            f"Error: {self}",
            "Ops, something went wrong :(",
            "Please contact support, will be fixed ASAP.",
            "Here's a funny cats compilation while you wait: https://youtu.be/DHfRfU3XUEo",
            "\n"
        ])
