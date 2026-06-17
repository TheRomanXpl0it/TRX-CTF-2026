import random
import signal
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

TIMEOUT = 60
FLAG = "TRX{y0u_c4n7_c0mb_TheHairyCoconut_https://en.wikipedia.org/wiki/Hairy_ball_theorem}"

def generate_rotation_matrix():
	theta = pi * random.randint(1, 2^16) / random.randint(1, 2^16)
	phi = pi * random.randint(1, 2^16) / random.randint(1, 2^16)
	v = vector([cos(theta)*sin(phi), sin(theta)*sin(phi), cos(phi)])
	
	theta = random.randint(1, 359)*pi/180

	u = v / v.norm()
	K = matrix([
		[0, -u[2], u[1]],
		[u[2], 0, -u[0]],
		[-u[1], u[0], 0]
	])
	R = matrix.identity(3) + sin(theta)*K + (1 - cos(theta))*(K*K)
	
	return R, v

def get_tangent(point, axis):
	return point.cross_product(axis).simplify_full()

def check_on_sphere(point):
	return (point.norm()^2 - 1).simplify_full().n() == 0

def read_point():
	print("Insert a point")
	x, y, z = var('x y z')
	v = vector([x, y, z])

	values = [SR(input("x: ")), SR(input("y: ")), SR(input("z: "))]
	v = vector([x.subs({x: values[0]}), y.subs({y: values[1]}), z.subs({z: values[2]})])
	if not check_on_sphere(v):
		print("point not on the sphere")
		exit()
	return v

def rotate(v, R):
	return v*R

def cipher(v, axis):
	t = get_tangent(v, axis)
	k = t*random.randint(2^127, 2^128)
	
	data = ','.join([str(c) for c in k])
	h = hashlib.sha256(data.encode()).digest()
	aes = AES.new(h, AES.MODE_ECB)
	ciphertext = aes.encrypt(pad(FLAG.encode(), AES.block_size))

	return ciphertext.hex()

def print_menu():
	print("Welcome to HB Key Generator!")
	print("1) Rotate a point")
	print("2) Encrypt")    

def main():
    R, axis = generate_rotation_matrix()

    can_rotate = 0
    print_menu()
    while True:
        choice = int(input("> "))
        if choice == 1:
            if can_rotate < 2:
                can_rotate += 1
                print(rotate(read_point(), R))
            else:
                print("can't rotate anymore")
                exit()
        elif choice == 2:
            print(cipher(read_point(), axis))
            exit()
        else:
            print("Invalid choice")
            exit()

if __name__ == "__main__":
    signal.alarm(TIMEOUT)
    main()
