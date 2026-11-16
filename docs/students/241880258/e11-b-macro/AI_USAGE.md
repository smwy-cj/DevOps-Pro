# AI_USAGE

工具：Codex，2026-11-11。

用于协助理解 E11-B macro 任务、编写测试和运行命令、整理验证记录。采纳内容包括精确比较 DEPS 补丁、检查 main.o 变量引用，以及保存验证结果的脚本。

参考实现来自课程实验包和组内现有代码。我的提交为 macro 扩展测试及证据脚本。本地 1 项测试通过，config.h、extra.h 只补到 DEPS 定义，main.o 保留 $(DEPS)，动态重检无 MISSING。日志见 work/e11-macro-241880258/。
