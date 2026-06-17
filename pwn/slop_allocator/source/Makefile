CC = gcc

slop: main.o slop.o
	$(CC) -o slop main.o slop.o
	rm -f *.o

main.o: main.c slop.h
	$(CC) -c main.c

slop.o: slop.c slop.h
	$(CC) -c slop.c

clean:
	rm -f *.o slop

run: slop
	./slop
