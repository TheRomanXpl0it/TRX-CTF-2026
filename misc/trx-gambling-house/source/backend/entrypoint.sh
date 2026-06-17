#!/bin/sh
set -eu

/app/backend/server.py &
exec socat TCP-LISTEN:${LAUNCHER_PORT:-1337},reuseaddr,fork,max-children=1 EXEC:/app/backend/launcher.py,pipes
