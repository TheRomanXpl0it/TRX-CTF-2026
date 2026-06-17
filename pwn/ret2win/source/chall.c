#include <stdio.h>
#include <string.h>
#include <windows.h>

const char art_base[] = "\n\n(IIIIIIIIIIIIIIIIIII)\n" \
")'.'.'.':;:;:'.'.'.'(\n" \
"('.'.'.;' | `:.'.'.')\n" \
")'.'.';'  |  `:'.'.'(\n" \
"('.'.;'   |   `:.'.')\n" \
")'.';'____|____`:'.'(\n" \
"(==@'     |     `@==)\n" \
")'.:     @()     :.'(\n" \
"('.'.   ()@()   .'.')\n" \
")'.'.  ()@()@)  .'.'(\n" \
"('.'.   _\\|/_   .'.')\n" \
")'.'.  |-----|  .'.'(\n" \
"('.'.___\\___/___.'.')\n" \
")'.'============='.'(\n" \
"('.'             '.')\n" \
" ~                 ~\n\n";


void MakeArt(LPSTR out, LPSTR name, SIZE_T len) {

    out[0] = '\0';
    if (len < sizeof(art_base)/sizeof(art_base[0])) {
        return;
    }

    strcpy(out, art_base);
    strncpy(out + sizeof(art_base)/sizeof(art_base[0]) - 1, name, len - sizeof(art_base)/sizeof(art_base[0]) + 1);
}

void ReadString(LPSTR buf) {
    fgets(buf, 300, stdin);
    buf[strcspn(buf, "\n")] = '\0';
} 

LPSTR GetPhrase() {
    printf("Enter your phrase: ");
    
    LPSTR phraseBuf = malloc(300 * sizeof(char));
    ReadString(phraseBuf);

    return phraseBuf;
}

void SaveArt(LPSTR art) {
    char path[256];
    printf("Enter the path to save the art: ");
    ReadString(path);
    puts("TODO: implement");
    return;
}

void PrintArt(LPSTR art) {
    puts(art);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    char buffer[sizeof(art_base)/sizeof(art_base[0]) + 253];

    LPSTR phrase = GetPhrase();
    MakeArt(buffer, phrase, sizeof(buffer)/sizeof(buffer[0]));
    PrintArt(buffer);

    SaveArt(buffer);

    return 0;
}