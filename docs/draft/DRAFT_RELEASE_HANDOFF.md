# DRAFT 发布交接记录

## 交付内容

| 内容 | 位置 | 当前状态 |
|---|---|---|
| 失败 Dockerfile | `draft-baseline/Dockerfile.broken` | 已有构建失败证据 |
| 成功 Dockerfile | `draft-baseline/Dockerfile.reference` | 已有构建成功证据 |
| 失败构建日志 | `draft-baseline/artifacts/build-failed.log` | UTF-8，SHA/大小已记录 |
| 成功构建日志 | `draft-baseline/artifacts/build-success.log` | UTF-8，SHA/大小已记录 |
| 运行日志 | `draft-baseline/artifacts/run-result.log` | UTF-8，输出 `hello DevOps` |
| 镜像 digest | `draft-baseline/artifacts/image-id.txt` | 与成功构建日志一致 |

## 发布步骤

1. 提交本次 DRAFT 契约、Artifact 和校验脚本。
2. 创建并推送 `draft-contract-v1` 标签。
3. 执行 `python scripts/validate-draft.py`，确认所有 Git Raw URL 可匿名读取。
4. 将成功镜像推送到公共容器仓库，并记录形如 `name@sha256:digest` 的引用。
5. 在无认证环境执行 `docker pull name@sha256:digest`，将镜像状态从 `RELEASE_BLOCKED` 改为 `ANONYMOUS_PULL_VERIFIED`。

## A06 阻塞问题对照表

| 阻塞问题 | 修改对照 | 验收证据 |
|---|---|---|
| Artifact 只有仓库相对路径，无法交接 | 所有 DRAFT 文件 Artifact 改为固定 `draft-contract-v1` 的 HTTPS Raw URL | `contracts/draft-success.json`、`contracts/draft-failure.json` |
| 缺少内容完整性元数据 | 每个文件记录 SHA-256 和 `size_bytes` | `scripts/validate-draft.py` 本地/远端字节校验 |
| 日志编码不统一 | 将 Docker 和运行日志统一为严格 UTF-8，并固定 LF | `draft-baseline/artifacts/*.log`、`.gitattributes` |
| 镜像只能依赖本地名称，不能按 digest 匿名拉取 | 成功结果记录 manifest digest，并设置公共仓库 digest 拉取发布门禁 | `output.image`、`--check-image` |
| 缺少一键复现的整体验收 | 新增自动校验脚本，串联 JSON、Artifact、编码、URL 和 digest 检查 | `python scripts/validate-draft.py` |

## 与 REPAIR 的边界

本发布只新增 DRAFT 标签和 DRAFT Artifact，不移动、重写或替换 `e2-contract-v1`。REPAIR 产物仍使用原有固定标签和校验记录。
