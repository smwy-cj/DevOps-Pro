# E2 DRAFT v3 验证记录

## 评审问题处理情况

| A06 阻塞项 | B06 修订 | 本地状态 |
|---|---|---|
| `DRAFT_001` 公共 Job 格式和自动校验缺失 | 三份 DRAFT JSON 改为 `1.0.0`，补齐公共字段并加入 Python/PowerShell 校验 | 通过 |
| `DRAFT_002` 输出不一致 | 源码、请求、成功结果和运行日志统一为 `hello DevOps` | 通过 |
| `DRAFT_003` 镜像不可取得 | 使用公共 GHCR 的 digest 引用；工作流已匿名拉取并运行 | 通过 |
| `DRAFT_004` 环境身份不完整 | 成功结果补齐提交、configuration、OS、架构、工具版本和 argv 命令 | 通过 |
| `DRAFT_005` Artifact 元数据和编码缺失 | Dockerfile及日志加入 URL、媒体类型、UTF-8、SHA-256、大小和读取方法 | 通过 |

## 本地校验

运行：

```sh
python3 -m pip install -r scripts/requirements-validation.txt
python3 scripts/validate-contract.py --skip-remote
```

2026-09-26 结果：`30/30 checks passed`。其中原 REPAIR 离线校验继续通过，DRAFT 新增校验覆盖三份 JSON Schema、请求与结果一致性、镜像 digest，以及五份本地产物的 UTF-8、SHA-256 和大小。完整输出保存在 `docs/e2/evidence/draft-v3-offline-validation.txt`。

补充运行 `make clean && make && ./hello`：构建成功并输出 `hello DevOps`。该本机构建只验证源码、命令和预期输出的一致性，不替代 Debian 容器环境证据。

使用 Docker CLI 匿名读取镜像清单：通过。清单媒体类型为 `application/vnd.docker.distribution.manifest.v2+json`，平台为 `linux/amd64`，配置 digest 为 `sha256:1c6f778ab5c14f694b06ce92e21aeadd22096ff1d95bafd60886f239b539e347`。

运行 `python3 scripts/verify-anonymous-image-pull.py`：通过。脚本未使用账号或 Registry 凭据，通过匿名 Bearer token 取得 manifest、config 和全部六层镜像 blob，共 `98,951,002` 字节，并逐一核对 digest 与大小。输出保存在 `docs/e2/evidence/draft-v3-anonymous-image-pull.txt`。

本机 Docker daemon 不可用，因此没有在本机启动容器。崔杰维护的 GitHub Actions 运行 `36227553388` 已完成 `docker logout ghcr.io` 后的实际 `docker pull` 和 `docker run`，仓库证据为 `anonymous-pull.log` 和 `anonymous-run.log`，运行输出为 `hello DevOps`。两份证据共同覆盖镜像匿名取得和实际运行。

本次 DRAFT v3 验证负责人为屠育玮；朱钱晨协助执行独立镜像取得和回归检查。

## 发布后校验

候选 JSON 引用尚未发布的 `e2-draft-contract-v3`。标签创建后运行：

```sh
python3 scripts/validate-contract.py
pwsh -File scripts/validate-contract.ps1
```

完整 Python 校验预计为 37 项，包括 A06 报告、五份 DRAFT Raw Artifact 和 GHCR 镜像清单。只有实际输出 `37/37 checks passed` 后才能将本记录改为发布完成并请求 A06 复评。
