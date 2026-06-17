#!/usr/bin/env python3.11

import ast
import os
import sys
from types import CodeType


def read_flag_from_file():
    flag_path = os.path.join(os.path.dirname(__file__), "flag")
    with open(flag_path) as f:
        return f.read().strip()


def main():
    user_input = input("> ").strip().encode()

    if any(x in b"(){}[].,'@_" for x in user_input) or not user_input.isascii():
        print("Sorry, you're trying to do something nasty...")
        exit(1)

    if len(user_input) > 10:
        print("I ain't reading all that")
        exit(1)

    try:
        ast.literal_eval(user_input.decode())
    except Exception:
        print("not good")
        exit(1)

    flag_from_file = read_flag_from_file()

    assert flag_from_file.startswith("TRX{") and flag_from_file.endswith("}"), "??? pls open a ticket"

    del flag_from_file

    print("Everything is good boss!!!!")

    sys.stdin.close()

    ((lambda:0).__class__(CodeType(0,0,0,0,0,0,user_input,(),(),(),"...","...","...",1,b"",b"",(),()),{}))()

if __name__ == "__main__":
    main()
