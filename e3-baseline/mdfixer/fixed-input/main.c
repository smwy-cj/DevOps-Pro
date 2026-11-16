#include <stdio.h>
#include <string.h>
#include "config.h"

int main(int argc, char **argv) {
    if (argc == 1) {
        printf("%d\n", VALUE);
    } else if (argc == 2 && strcmp(argv[1], "--double") == 0) {
        printf("%d\n", 2 * VALUE);
    } else {
        fprintf(stderr, "usage: app [--double]\n");
        return 2;
    }
    return 0;
}
