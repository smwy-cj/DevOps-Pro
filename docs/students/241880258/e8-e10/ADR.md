# E8—E10 共同实验决策记录

学号：241880258；角色：成员三；轨道：B；日期：2026-11-03。

本次按最新任务范围完成个人分支上的共同实验、运行证据、报告、现有测试、PR 与 CI 归档。扩展测试和实现改动延后。本次未更改 lab.py、test_profile.py 或公共 workflow。

采用资料包 B 组逐步手册，通过 classroom_helpers.sh 在 Docker 内执行每个 Python 步骤。宿主环境选用本机 WSL Ubuntu Linux，替代手册中的远程 SSH Linux 服务器；仍使用课程 Dockerfile、个人镜像标签、禁网容器及 SYS_PTRACE。这样可以在当前设备保留真实运行证据，无需依赖尚未提供的服务器登录信息。

B 组使用本次 scan() 生成的固定报告，不将其表述为与 A 组远程联调。报告的 commit 绑定内层样例 Git HEAD；student-source-commit.txt 记录外层学生仓库版本，两者分别保存。

只为 MISSING 生成候选，不删除 REDUNDANT。direct 风格修改目标依赖行，macro 风格修改 DEPS 定义，mixed 风格保留变量引用并修改目标依赖行。纯变量被多个目标共享时的影响范围尚需后续扩展验证，本次仅运行手册定义的样例。

候选先在 sandbox 内完成应用、构建、功能测试、头文件变化与无 MD 重检，全部通过后才写回 Makefile。拒绝时用原字节比较确认源文件保持；rollback 字段表示原文件保持，并不意味着曾先写坏原文件再恢复。

验证和原始结果见个人报告及归档中的 work/。质量门成功仅证明受限 C/Make 教学配置通过，不能据此宣称完整实现论文工具或完成 E11—E12 跨组联调。
