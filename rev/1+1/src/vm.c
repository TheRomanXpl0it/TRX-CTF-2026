#include <unistd.h>
#include <stdbool.h>
#include <fcntl.h>
#include <sys/stat.h>

typedef long long ll;

void put_num(unsigned long long n) {
	if (n > 15)
		put_num(n / 16);
	write(1, &"0123456789abcdef"[n % 16], 1);
}

int main(int argc, char **argv) {
	if (argc != 2) {
		return 1;
	}

	int fd = open(argv[1], O_RDONLY);
	struct stat s;
	fstat(fd, &s);
	s.st_size /= 8;
	
	ll prog[s.st_size];
	ll r = read(fd, prog, s.st_size * 8);
	if (r != s.st_size * 8) {
		return 1;
	}

	ll pc = 0;
	while (pc >= 0 && pc < s.st_size) {
		ll a = prog[pc];
		ll b = prog[pc+1];
		ll c = prog[pc+2];

		bool branch = true;

		if (a == -1) {
			char buf[1];
			read(0, buf, 1);
			prog[b] = buf[0];
		} else if (a == -2) {
			put_num(prog[b]);
			write(1, " ", 1);
		} else {
			prog[b] += prog[a];
			if (prog[b] > 0) {
				branch = false;
			}
		}

		if (branch) {
			pc = c;
		} else {
			pc += 3;
		}
	}

	return 0;
}
