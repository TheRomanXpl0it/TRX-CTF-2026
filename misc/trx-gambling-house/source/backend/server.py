#!/usr/bin/env python3

import signal
from sui_ctf_sandbox.service import ChallengeService

def main() -> None:
    service = ChallengeService()

    def stop(*_args) -> None:
        service.stop_sui()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    service.start_sui()
    while True:
        signal.pause()

if __name__ == "__main__":
    main()