# Macro 风格参考修复

main.o 通过 DEPS 宏声明依赖。
参考修复在 DEPS 中加入 config.h，保留原有 Makefile 风格。
