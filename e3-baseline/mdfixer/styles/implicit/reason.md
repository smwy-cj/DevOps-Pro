# Implicit 风格参考修复

原项目使用隐式 %.o: %.c 规则。
参考修复使用 -MMD -MP 生成 main.d，并通过 -include main.d 读取头文件依赖。
编译后 main.d 应声明 main.o 同时依赖 main.c 和 config.h。
