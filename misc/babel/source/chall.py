#!/usr/bin/env python3
import re


def is_forbidden(code):
	import ast

	blacklist = [
		"__subclasses__", "__class__", "__globals__",
		"__doc__", "__base__", "__import__", "mro",
		"breakpoint", "__import__", "eval", "exec", "compile",
		"open", "__setattr__", "flag"
	]

	for c in ast.walk(ast.parse(code)):
		if any(isinstance(c, t) for t in (
			ast.Module,
			ast.For,
			ast.Tuple,
			ast.Store,
			ast.Load,
			ast.Expr
		)):
			continue

		match type(c):
			case ast.ClassDef:
				if c.name in blacklist or c.decorator_list:
					return True

			case ast.Global:
				if any(n in blacklist for n in c.names):
					return True

			case ast.Name:
				if c.id in blacklist:
					return True

			case ast.Attribute:
				if c.attr in blacklist:
					return True

			case _:
				return True
	
	return False

		


def main():
	import sys

	_exec = exec

	dangerous_builtins = ["breakpoint", "__import__", "eval", "exec", "compile", "open"]

	code = input(">>> ")
	
	if len(code) > 900:
	    exit(1)

	if is_forbidden(code):
		exit(1)

	if not re.fullmatch(rf"[a-z_:.,\s]+", code):
		exit(1)

	for x in dangerous_builtins:
		delattr(__builtins__, x)

	sys.stdin.close()
	sys.stderr.close()

	del sys

	_exec(code,{'__builtins__': {'__build_class__': __build_class__,}}, {})

if __name__ == '__main__':
	main()
