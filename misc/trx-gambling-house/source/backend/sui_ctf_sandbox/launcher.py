from dataclasses import dataclass
from typing import Callable
from .exceptions import SuiCTFSandboxError
from .service import ChallengeService
from .utils import render_json

@dataclass(frozen=True)
class Action:
    name: str
    handler: Callable[[ChallengeService], object]

def create_instance_action() -> Action:
    def handler(service: ChallengeService) -> dict:
        return {"ok": True, "instance": service.create_instance()}
    return Action(name="create new instance", handler=handler)

def get_connection_info_action() -> Action:
    def handler(service: ChallengeService) -> dict:
        return {"ok": True, "instance": service.current_connection_info()}
    return Action(name="get connection info", handler=handler)

def get_flag_action() -> Action:
    def handler(service: ChallengeService) -> dict:
        return service.check_flag()
    return Action(name="get flag", handler=handler)

def quit_action() -> Action:
    def handler(service: ChallengeService):
        return None
    return Action(name="quit", handler=handler)

def actions() -> list[Action]:
    return [
        create_instance_action(),
        get_connection_info_action(),
        get_flag_action(),
        quit_action(),
    ]

def menu_prompt() -> str:
    rows = [f"{index}) {action.name}" for index, action in enumerate(actions(), start=1)]
    return "\n".join(rows) + "\n> "

def run_launcher(service: ChallengeService) -> int:
    action_list = actions()
    print(menu_prompt(), end="")
    try:
        index = int(input()) - 1
        if index < 0 or index >= len(action_list):
            print("invalid option")
            return 1
        if index == len(action_list) - 1:
            return 0
        if index == 0:
            print("creating instance...")
        print(render_json(action_list[index].handler(service)))
        return 0
    except ValueError:
        print("invalid option")
        return 1
    except SuiCTFSandboxError as exc:
        print(exc.message(), end="")
        if exc.details:
            print(render_json({"details": exc.details}))
        return 1
    except KeyboardInterrupt:
        print("\nExiting.")
        return 0
