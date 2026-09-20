# DRAFT Build Baseline

本项目用于验证DRAFT根据项目文档和Docker构建日志生成、修复Dockerfile的能力。

## 固定版本

- Repository: https://github.com/smwy-cj/DevOps-Pro
- Commit: `3828e6e5e6f7ea27c25b0d627edef9e06b433152`
- Build command: `make`
- Verify command: `./hello`
- Expected output: `hello E3`

## 项目结构

```text
draft-baseline/
├── src/
│   └── hello.c
├── artifacts/
│   ├── build-failed.log
│   ├── build-success.log
│   ├── run-result.log
│   └── image-id.txt
├── Makefile
├── Dockerfile.broken
├── Dockerfile.reference
└── README.md
```

## 失败基线

`Dockerfile.broken`没有安装GNU Make和GCC。

执行：

```bash
docker build --no-cache -f Dockerfile.broken -t draft-broken .
```

预期失败信息：

```text
make: not found
exit code: 127
```

完整日志位于：

```text
artifacts/build-failed.log
```

## 修复方法

`Dockerfile.reference`安装以下依赖：

- `make`
- `gcc`
- `libc6-dev`

## 成功构建

执行：

```bash
docker build --no-cache -f Dockerfile.reference -t draft-reference .
```

构建成功后生成：

```text
draft-reference:latest
```

完整日志位于：

```text
artifacts/build-success.log
```

## 功能验证

执行：

```bash
docker run --rm draft-reference
```

预期输出：

```text
hello E3
```

运行日志位于：

```text
artifacts/run-result.log
```

## DRAFT处理流程

1. 读取项目源码、Makefile和README；
2. 使用初始Dockerfile构建项目；
3. 从日志识别`make: not found`；
4. 在Dockerfile中安装构建工具；
5. 重新构建镜像；
6. 运行容器并验证输出。