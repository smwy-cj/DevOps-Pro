# A06/B06 REPAIR 接口提案

状态：B06 提案 v1.0.0，等待 A06 书面确认。

## 端点

- `POST /v1/repair-jobs`：创建修复任务。有效请求返回 HTTP 202 和服务端生成的 `job_id`。
- `GET /v1/jobs/{job_id}`：查询任务状态、结果或系统错误。
- 契约阶段只定义请求和响应，不要求 E2 部署服务。

## 请求公共字段

创建请求必须包含：

- `schema_version`
- `trace_id`
- `idempotency_key`
- `job_type`，REPAIR 端点固定为 `REPAIR`
- `input`

`job_id`、`status` 和时间戳由服务端产生，不放在创建请求中。

## REPAIR 输入

`input` 必须包含：

- `repository`：仓库 URL、完整 40 位 commit SHA、项目子目录。
- `configuration`：唯一配置对象，包含 `configuration_id`、系统、体系结构、工具版本和构建命令。
- `error_report`：报告 ID、Artifact 引用和明确的读取方法。
- `finding`：从报告中选出的 finding 摘要，只允许 `MISSING`。
- `makefile_path`：相对于 `repository.subdirectory` 的路径。
- `verification`：增量重建的变化文件、预期目标和检查方法。

不再保留与 `configuration` 重复的 `environment` 字段。

`input.configuration` 与 A06 固定报告的 `configuration` 同形；`input.finding` 是该报告中待修复 finding 的选择摘要。服务端下载报告后，必须核对摘要与原报告一致，不能把摘要当作独立检测结论。

## 成功结果与验证含义

- `output.patch` 指向可应用的 Git Patch，`output.repair_report` 指向修复报告；两者记录生产任务、源码提交、构建配置、SHA-256 和字节数。
- 修复报告记录 `declaration_style` 和 `style_rationale`。本例为 `TARGET`，直接给 `main.o` 规则增加 `config.h`。
- `output.provenance` 和修复报告的 `provenance` 区分 `MANUAL_REFERENCE` 与真正的 `MDFIXER_RUN`。本次成功 Job 是 E2 契约样例，补丁及增量构建经过人工实测；示例时间戳和 `job_id` 不代表 MDFixer 服务已运行。
- `verification.recheck` 必须显式记录。当前为 `NOT_RUN`，因为 BuildChecker 尚未实现；不得把人工构建行为测试记作检测器重检通过。后续若写成 `PASSED`，须附检测任务 ID 和结果产物。

路径基准：请求、修复报告和 `modified_files` 中的项目路径相对于 `repository.subdirectory`；Git Patch 中的 `a/`、`b/` 路径相对于**仓库根目录**，以便在仓库根目录运行 `git apply`。

## Artifact 语义

`artifact.media_type` 表示解码后产物的逻辑格式。`read_method.response_media_type` 表示 HTTP 响应头，两者可以不同。

本例中：

- 报告逻辑格式为 `application/json`；
- Gitee Raw 响应头为 `text/plain; charset=utf-8`；
- 消费方必须按 UTF-8 解码后解析 JSON；
- Artifact 记录 SHA-256 和字节数用于完整性校验。

输出产物使用 Git 标签 `e2-contract-v1` 的 Raw URL。合并文件后必须创建并推送该标签，才能让 URL 可读取且保持不可变。
在标签创建前，这些 URL 是待发布引用，不能作为已可下载的产物交给 A06 验收。

## REPAIR 拒绝规则

| 错误码 | 条件 | 可重试 |
|---|---|---|
| `REPAIR_7001` | finding 类型不是 `MISSING` | 否 |
| `REPAIR_7002` | 请求 commit 与报告或 finding commit 不一致 | 否 |
| `REPAIR_7003` | 请求 configuration 与报告或 finding configuration 不一致 | 否 |
| `REPAIR_7004` | 报告引用与读取地址或报告内容不一致 | 否 |

这些错误码是 B06 提案。A06 如希望复用 `REQUEST_1001`，双方必须在 ADR 中记录最终映射，并同步修改 Schema 与样例。

## 校验顺序

1. 按 `task.schema.json` 做结构校验。
2. 下载并校验 ERROR_REPORT 的状态码、大小和 SHA-256。
3. 检查 Artifact URI 与 `read_method.url` 一致。
4. 检查 finding 类型、commit 和 configuration。
5. 仅在全部通过后创建异步 Job。

JSON Schema 可以拒绝 `REDUNDANT`，但无法使用标准关键字比较多个字段的值。commit 和 configuration 的跨字段一致性由服务端语义校验完成，示例脚本实现了相同检查。
