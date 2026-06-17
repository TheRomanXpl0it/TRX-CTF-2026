from pwn import *
import ast

user_input = b'U"|\x14F!|\x14S"'
print(ast.literal_eval(user_input.decode()))
