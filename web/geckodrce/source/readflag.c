// readflag.c
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
  if (argc != 2 || strcmp(argv[1], "pls") != 0) {
    write(1, "ask politely :(\n", 16);
    return 1;
  }

  int fd = open("/flag.txt", O_RDONLY);
  if (fd < 0) return 1;

  char buf[128];
  ssize_t n = read(fd, buf, sizeof(buf));
  if (n > 0) write(1, buf, (size_t)n);

  close(fd);
  return 0;
}
