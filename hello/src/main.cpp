#include <stdio.h>

#ifndef HELLO_BUILD
#define HELLO_BUILD "manual"
#endif
#ifndef HELLO_COMPILER
#define HELLO_COMPILER "unknown"
#endif
#ifndef HELLO_SYSTEM
#define HELLO_SYSTEM "unknown"
#endif
#ifndef HELLO_ARCH
#define HELLO_ARCH "unknown"
#endif

int main() {
#ifdef HELLO_SHOUT
    const char *greeting = "HELLO, WORLD";
#else
    const char *greeting = "hello, world";
#endif
    printf("%s\n", greeting);
    printf("config: %s\n", HELLO_BUILD);
    printf("compiler: %s\n", HELLO_COMPILER);
    printf("system: %s\n", HELLO_SYSTEM);
    printf("arch: %s\n", HELLO_ARCH);
    return 0;
}
