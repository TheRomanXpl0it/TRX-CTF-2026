#include "slop.h"
#include <stdio.h>
#include <stdlib.h>

#define MAX_NOTES 16
#define MAX_SPACESHIPS 64

#define ALLOC_SPACESHIP 1
#define ALLOC_NOTE 2
#define FREE_NOTE 3
#define TAKE_OFF 4
#define MAX_CMD 4

typedef struct spaceship {
    uint8_t permission;  
    char* notes[MAX_NOTES];
} spaceship;

spaceship *spaceships[MAX_SPACESHIPS];
uint32_t n_spaceships = 0;

void banner()
{
    puts("                                                          ");
    puts("                                        ████████▓▓████    ");
    puts("                                  ██████████        ▓▓    ");
    puts("                              ▓▓██▓▓██              ▓▓    ");
    puts("                          ██▓▓▓▓                  ████    ");
    puts("                        ▓▓████      ▓▓██          ██      ");
    puts("                      ██▓▓        ▓▓██████      ████      ");
    puts("                    ▓▓▓▓        ████░░░░████    ██▓▓      ");
    puts("          ██████████▓▓          ████░░░░████  ██▓▓        ");
    puts("        ██▓▓    ▒▒██              ████████    ▓▓██        ");
    puts("        ▓▓    ▒▒██                  ████    ▓▓▓▓          ");
    puts("      ████  ▒▒██          ▓▓██            ▓▓██            ");
    puts("      ██▒▒  ▒▒▓▓  ░░    ▓▓▓▓▒▒██          ████            ");
    puts("    ██▓▓▒▒▒▒██        ████▒▒██▒▒        ████              ");
    puts("    ██████████▓▓    ▓▓▓▓▒▒▓▓▒▒        ████                ");
    puts("            ░░    ████▒▒██▒▒        ██▓▓                  ");
    puts("      ░░░░        ██▒▒██▒▒        ▓▓██                    ");
    puts("    ▒▒▒▒░░        ▒▒██▒▒        ██▒▒██                    ");
    puts("  ░░▒▒▒▒▒▒░░                ▓▓▓▓  ▒▒██                    ");
    puts("        ▒▒░░          ░░████▒▒    ▒▒▓▓                    ");
    puts("      ▒▒▒▒▒▒░░    ░░  ▒▒██▒▒      ▒▒██                    ");
    puts("    ▒▒▒▒▒▒▒▒░░░░▒▒░░  ▒▒██▒▒▒▒▓▓████                      ");
    puts("  ░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░▒▒██▓▓████                          ");
    puts("  ▒▒      ▒▒▒▒▒▒░░▒▒░░  ▓▓▓▓                              ");
    puts("        ▒▒▒▒▒▒  ▒▒▒▒                                      ");
    puts("        ▒▒░░    ▒▒░░                                      ");
    puts("                                                          ");
    puts("                                                          ");

    puts("=== NASA SPACESHIP MEMORY MANAGEMENT SYSTEM ===");
    puts("");
    puts("Greetings, Engineer!");
    puts("I have been asked by NASA to build a memory allocator for the new kernel they are developing");
    puts("that will be shipped in the next generation of spaceships heading to Mars.");
    puts("");
    puts("The current prototype allocator is called SLOP: The SLAB Orbital Page allocator.");
    puts("I prepared this simulation to test the robustness of the allocator.");
    puts("");
    puts("Good luck, and may your memory management skills guide us to the stars!");
}

void menu()
{
    printf("\n");
    printf("1) Allocate Spaceship\n");
    printf("2) Allocate Note\n");
    printf("3) Free Note\n");
    printf("4) Take Off\n");
    printf("> ");
}

size_t read_input()
{
    size_t input;

    scanf("%zu", &input);

    while(getchar() != '\n');

    return input;
}

spaceship *pick_spaceship()
{
    printf("Pick a spaceship (0 - %d)\n", MAX_SPACESHIPS - 1);
    printf("> ");
    
    size_t idx = read_input();

    if (idx >= MAX_SPACESHIPS) {
        puts("Sorry we don't have that many spaceships :(");
        return NULL;
    }

    if (!spaceships[idx]) {
        puts("This spaceship is not available!");
        return NULL;
    }

    return spaceships[idx];
}

void exec_cmd(size_t cmd)
{
    spaceship *falcon;
    size_t idx;

    switch (cmd) {
    case ALLOC_SPACESHIP:
        if (n_spaceships >= MAX_SPACESHIPS) {
            puts("You have too many spaceships!");
            return;
        }

        falcon = (spaceship *)slop_alloc(sizeof(spaceship));

        falcon->permission = 0;

        for (size_t i = 0; i < MAX_NOTES; i++) 
            falcon->notes[i] = 0;

        printf("Spaceship allocated at index: %u\n", n_spaceships);

        spaceships[n_spaceships++] = falcon;

        break;

    case ALLOC_NOTE:
        falcon = pick_spaceship();

        if (!falcon)
            return;

        printf("Pick a slot for this note (0 - %d)\n", MAX_NOTES - 1);
        printf("> ");

        idx = read_input();

        if (idx >= MAX_NOTES) {
            printf("You can store at maximum %d notes for spaceship\n", MAX_NOTES);
            return;
        }

        if (falcon->notes[idx]) {
            puts("This slot is full");
            return;
        }

        puts("Enter the note length");
        printf("> ");
        
        size_t len = read_input();
        
        char* note = (char *)slop_alloc(len);

        if (!note) {
            puts("Note allocation failed!");
            return;
        }
        
        falcon->notes[idx] = note;

        puts("Write your note");
        printf("> ");

        fgets(note, len, stdin);

        break;

    case FREE_NOTE:
        falcon = pick_spaceship();

        if (!falcon)
            return;

        printf("Pick the note to remove (0 - %d)\n", MAX_NOTES - 1);
        printf("> ");

        idx = read_input();

        if (idx >= MAX_NOTES) {
            puts("We don't have that many notes");
            return;
        }

        if (!falcon->notes[idx]) {
            puts("This slot is already empty");
            return;
        }

        slop_free(falcon->notes[idx]);
        falcon->notes[idx] = NULL;

        break;

    case TAKE_OFF:
        puts("WARNING: Only spaceships with special permissions can takeoff");
        falcon = pick_spaceship();

        if (!falcon)
            return;

        if (!falcon->permission) {
            puts("This spaceship doesn't have the right permission to flight");
        } else {
            printf("Spaceship n. %p taking off...\n", falcon);
            printf("ERROR: this is a simulation!\n");
        }

        break;

    default:
        break;
    }
}

int main()
{
    size_t cmd;

    setbuf(stdin, NULL);
    setbuf(stdout, NULL);
    setbuf(stderr, NULL);

    slop_init();
    banner();

    while (1) {
        cmd = MAX_CMD + 1;
        menu();
        cmd = read_input();

        if (cmd > MAX_CMD)
            exit(1);

        exec_cmd(cmd);        
    }

    return 0;
}
