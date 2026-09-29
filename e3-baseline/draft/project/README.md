# B06 E3 Tiny Greeting

## 用途

这是 B06 为 E3 准备的 DRAFT 测试项目。
人工预期结果来源为 MANUAL_REFERENCE。

## 本机构建

构建命令：

make clean
make

成功判据：

- make 退出码为 0
- 生成可执行文件 hello

## 功能验证

验证命令：

./hello

成功判据：

- 退出码为 0
- 标准输出严格等于 hello E3

## 清理

make clean

## 项目范围

本项目包含 src/hello.c 和 GNU Make 构建规则。
macOS 构建用于检查源码、命令和预期输出的一致性。
Docker 样本保存在上一级目录。
