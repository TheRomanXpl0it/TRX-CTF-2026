#!/usr/bin/env python3

from sui_ctf_sandbox.launcher import run_launcher
from sui_ctf_sandbox.service import ChallengeService

if __name__ == "__main__":
    raise SystemExit(run_launcher(ChallengeService()))