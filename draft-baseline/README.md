# DRAFT Build Baseline

本项目用于验证DRAFT根据项目文档和Docker构建日志生成、修复Dockerfile的能力。

## 固定版本

- Repository: https://github.com/smwy-cj/DevOps-Pro
- Commit: `3828e6e5e6f7ea27c25b0d627edef9e06b433152`
- Build command: `make`
- Verify command: `./hello`
- Expected output: `hello DevOps`

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
hello DevOps
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

## DRAFT v2 镜像与证据

`.github/workflows/draft-reference.yml` 在 `dev` 的 DRAFT 源码、Makefile 或参考 Dockerfile 更新时运行，也可以手动触发。它从 `Dockerfile.reference` 无缓存构建、运行容器并断言输出恰好为 `hello DevOps`，然后把镜像发布至 `ghcr.io/smwy-cj/devops-pro/draft-reference:dev-<commit-sha>`。

2026-09-26 的[构建运行记录](https://github.com/smwy-cj/DevOps-Pro/actions/runs/36226968640)已成功，源码提交为 `09bab8573f008425e2fc087c71a16634bed64e7e`。仓库内 `artifacts/build-success.log` 和 `artifacts/run-result.log` 已由该次构建的 UTF-8 工件替换，`artifacts/image-digest.txt` 记录完整镜像地址：

```text
ghcr.io/smwy-cj/devops-pro/draft-reference@sha256:f261c3e4893143e37caed1df2ec662244c699db0d0b3848e97f1ddce3f49d472
```

首次发布的 GHCR 包可能默认为私有。发布成功后在 GitHub Package 的设置中将可见性改为 Public，再在未登录 GHCR 的环境中执行工件提供的完整 digest 地址：

```bash
docker logout ghcr.io
docker pull ghcr.io/smwy-cj/devops-pro/draft-reference@sha256:<工作流输出的64位摘要>
docker run --rm ghcr.io/smwy-cj/devops-pro/draft-reference@sha256:<工作流输出的64位摘要>
```

匿名拉取和输出均通过后，才在验收提交上创建 `e2-draft-contract-v2` Git 标签，并记录其提交 SHA、工作流运行地址与镜像 digest。当前尚未完成公开可见性和匿名拉取验收。
