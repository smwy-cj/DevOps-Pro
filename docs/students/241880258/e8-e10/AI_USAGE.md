# AI 使用记录

姓名：庄子宣；学号：241880258；日期：2026-11-03。

工具：Codex；日期：2026-11-03。

用途：协助我理解 B 组实验要求、编写操作命令，完善 E9 重复 MD 去重实现和测试。

采纳内容：patch() 按 (target, dependency) 去重，新增 Student241880258E9Tests 测试类和三种风格的证据脚本。

操作与验证：我在个人分支中完成代码提交，在课程容器中验证基础实验和扩展，比较 Patch、plan 及原 Makefile 字节。

结果：direct、macro、mixed 均只添加一次 config.h，plan 只有一项，原文件不变；12 项测试通过，退出码 0。日志：work/e9-duplicate-md/after-fix-tests.log。

参考实现来自课程实验包。我的个人新增内容为重复 MD 去重修改、两项测试及验证记录。B 组 E8—E10 基础实验也已完成，证据保存在各自 OUT 中。
