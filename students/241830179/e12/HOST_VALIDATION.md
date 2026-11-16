# 前置检查记录

环境：Windows，Python 3.15.2，MinGW GCC/GNU Make，Git。
本记录描述前置阶段的 Windows 预检。后续 Linux Docker/strace 全流程与独立复验
已于 2026-11-13 完成，正式结果见 [ACCEPTANCE.md](ACCEPTANCE.md)。

- 原有接口契约测试 11 项通过，包括本机 HTTP 202/409 幂等冲突测试。
- 新增项目适配测试 8 项通过，包含真实 GCC 编译、嵌套目录补丁应用、头文件变更
  触发重建、测试失败保持源文件、过期报告拒绝及缓存失效。
- 交付工具测试 4 项通过：版本清单及 Docker 候选契约、产物哈希/路径校验、
  防止覆盖已有准备目录、中文产物文件名的编码与下载完整性。

共 23 个不同测试用例通过，分别通过对应测试命令验证。早期组合运行日志含 19
项（11 个原有测试及 8 个适配测试）；适配测试在头文件语义变化检查加入后重跑。

```sh
python -m unittest discover -s labs/e11e12 -p 'test_*.py' -v
```

所选项目额外使用目标完整 SHA 的干净检出副本做了 Windows 预检：

1. GCC 依赖扫描实际发现 `main.o -> config.h` 为 MISSING。
2. 适配器实际生成仓库相对路径补丁，`git apply --check` 和应用成功。
3. 本机构建与三项功能测试通过。
4. 将验证副本的 VALUE 从 1 改为 2 后，普通构建重新生成 main.o，功能测试
   验证普通输出为 2、--double 为 4，非法参数返回 2。
5. 修复后 GCC 扫描没有剩余 MISSING，原项目头文件保持原值。

本机预检的 clean 命令使用 Python 删除临时构建输出，编译器与 Make 使用本机
程序路径；正式请求使用 Linux 的 make/gcc/python3。两类证据不能互相替代。

可检查 `evidence/windows-native-preflight.json`、`evidence/adapter-tests.txt`、
`evidence/contracts-and-adapter-tests.txt`、`evidence/handoff-tests.txt`。
语法编译与 `git diff --check` 通过。候选 Dockerfile 已通过现有 DRAFT 的
`prepare_candidate` 契约检查；镜像构建和运行留给本人执行。
