from .launcher import run_launcher
from .service import ChallengeService

def main() -> None:
    raise SystemExit(run_launcher(ChallengeService()))