#!/bin/sh
set -eu

VM_BIN="/app/vm"
if [ ! -x "$VM_BIN" ]; then
  VM_BIN="$(dirname "$0")/vm"
fi

while true; do
  "$VM_BIN" || true
done
