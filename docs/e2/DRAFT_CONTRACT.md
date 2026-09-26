# A06/B06 DRAFT 接口契约 v3 候选版

## 状态

本文件回应 A06 在提交 `723c0e856897979f896cd3f3505de62bc56a0842` 中提出的 DRAFT 修改要求。候选版本合入并发布 `e2-draft-contract-v3` 前，不得对外宣称 A06 已接受 DRAFT 联调基线。已接受的 REPAIR 标签 `e2-contract-v1` 保持不变。

## 请求

`contracts/draft-request.json` 使用公共异步 Job 创建请求：

- `schema_version` 固定为 `1.0.0`；
- `job_type` 固定为 `DRAFT`；
- 请求携带 `trace_id` 和 `idempotency_key`；
- `input.repository` 固定仓库、40 位提交和项目子目录；
- `input.configuration` 记录配置编号、OS、架构、工具版本和 argv 形式的 clean/build/verify 命令；
- `documents` 和 `expected_output` 中的路径相对于 `repository.subdirectory`。

本基线统一预期输出为 `hello DevOps`。

## 成功结果

成功 Job 回显完整 `input`，并在 `output` 中返回：

- `repository_commit` 和完整 `configuration`；
- Dockerfile、构建日志和运行日志 Artifact；
- 固定到 digest 的 GHCR 镜像引用和 `docker pull` argv；
- 构建、验证退出码和实际输出。

镜像引用可以直接映射到 A06 `FULL_CHECK.input.runtime_environment.image`，digest 映射到 `image_digest`，configuration 映射到 `runtime_environment`，commands 映射到 `input.build`。

## 失败结果

失败样例使用公共错误码 `ENV_3002`。失败结果仍返回导致失败的 Dockerfile 和构建日志 Artifact，便于调用方复核；完整日志不写入错误消息。

## Artifact 读取

DRAFT 的 Dockerfile 和日志 Artifact 必须包含：

- 匿名 HTTPS URL；
- 逻辑媒体类型与 UTF-8 编码；
- `producer_job_id`、`repository_commit` 和 `configuration_id`；
- SHA-256 与字节数；
- `read_method`，其中 URL 必须与 Artifact URI 一致。

候选 JSON 使用 `e2-draft-contract-v3` Raw URL。标签发布前这些 URL 尚不可用，只允许执行离线校验；标签发布后必须执行完整联网校验。

## 镜像

固定镜像为：

```text
ghcr.io/smwy-cj/devops-pro/draft-reference@sha256:b2dbfef36913f7322287f155650cea3f064d2986d414700e916f87404402d2c7
```

镜像清单可匿名读取，平台为 `linux/amd64`。GitHub Actions 运行 `36227553388` 已在退出 GHCR 登录后按 digest 拉取并运行，输出为 `hello DevOps`。

屠育玮负责的独立交付验证还通过匿名 Registry API 下载了 manifest、config 和全部六层镜像 blob，总计 `98,951,002` 字节。每个 blob 的 SHA-256 和字节数均与 manifest 一致，证据见 `docs/e2/evidence/draft-v3-anonymous-image-pull.txt`。该验证没有使用 GitHub 账号、PAT 或 Docker Registry 登录信息。
