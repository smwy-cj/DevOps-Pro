# Target 风格参考修复

原声明为 main.o: main.c。
main.c 实际读取 config.h，因此在同一目标声明中补充 config.h。
预期修复后只修改 config.h 即可触发 main.o 重新编译。
