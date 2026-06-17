import json
from pathlib import Path
from pydantic import BaseModel

def render_json(payload: object) -> str:
    if isinstance(payload, BaseModel):
        return payload.model_dump_json(indent=2)
    return json.dumps(
        payload,
        indent=2,
        default=lambda value: value.model_dump() if isinstance(value, BaseModel) else str(value),
    )

def write_json(path: Path, value: object) -> None:
    path.write_text(render_json(value) + "\n", encoding="utf8")

def read_json(path: Path, default):
    return default if not path.exists() else json.loads(path.read_text(encoding="utf8"))