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

`.github/workflows/draft-reference.yml` 在 `dev` 的工作流、DRAFT 源码、Makefile 或参考 Dockerfile 更新时运行，也可以手动触发。它重新生成失败构建日志，随后从 `Dockerfile.reference` 无缓存构建、运行容器并断言输出恰好为 `hello DevOps`，最后把镜像发布至 `ghcr.io/smwy-cj/devops-pro/draft-reference:dev-<commit-sha>`。

2026-09-26 的[最终构建运行记录](https://github.com/smwy-cj/DevOps-Pro/actions/runs/36227553388)已成功，工作流源码提交为 `6e976ba21184aa77071fa1861054e850232c0f11`。仓库内 `artifacts/build-failed.log`、`artifacts/build-success.log`、`artifacts/run-result.log` 已由该次构建的 UTF-8 工件替换，`artifacts/image-digest.txt` 记录完整镜像地址：

```text
ghcr.io/smwy-cj/devops-pro/draft-reference@sha256:b2dbfef36913f7322287f155650cea3f064d2986d414700e916f87404402d2c7
```

同一工作流已在 `docker logout ghcr.io` 后按 digest 执行 `docker pull` 与 `docker run`，镜像被成功下载并输出 `hello DevOps`。对应证据为 `artifacts/anonymous-pull.log` 与 `artifacts/anonymous-run.log`。交付方可在自己的未登录环境再次复核：

```bash
docker logout ghcr.io
docker pull ghcr.io/smwy-cj/devops-pro/draft-reference@sha256:b2dbfef36913f7322287f155650cea3f064d2986d414700e916f87404402d2c7
docker run --rm ghcr.io/smwy-cj/devops-pro/draft-reference@sha256:b2dbfef36913f7322287f155650cea3f064d2986d414700e916f87404402d2c7
```

以上匿名拉取与运行已由云端 Runner 验证。首次未带 token 的 `401` 是 Registry 的标准挑战响应，不表示镜像私有。
