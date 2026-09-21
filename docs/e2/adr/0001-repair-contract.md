# ADR 0001：A06/B06 REPAIR 请求与产物契约

- 状态：Proposed
- 日期：2026-09-21
- 决策方：B06 提案，等待 A06 确认

## Context

A06 提供了绑定固定源码提交和构建配置的 MISSING 报告。B06 需要据此给出 REPAIR 请求、成功结果和三类拒绝样例。现有请求重复表示 `configuration` 与 `environment`，缺少幂等键，并且没有约定相对路径的基准。

A06 的报告包含 `declaration_location`，但 A06 当前 `common.schema.json` 的 `$defs.finding` 设置了 `additionalProperties: false`，且没有声明该字段。这会导致报告中的 finding 无法通过该公共定义。

## Decision

1. 创建请求使用 `schema_version`、`trace_id`、`idempotency_key`、`job_type` 和 `input`。`job_id` 与状态由服务端产生。
2. REPAIR 使用单一 `configuration` 对象。该对象与 A06 报告中的 configuration 同形，包含环境标识和构建命令，不再另设重复的 `environment`。
3. ERROR_REPORT 是 detector 和 evidence 的权威来源。请求中的 `finding` 是待修复项的选择摘要，保留定位修复所需的 `declaration_location`。
4. `makefile_path`、finding 中的路径和验证文件路径均相对于 `repository.subdirectory`。
5. Artifact 的 `media_type` 表示逻辑格式，HTTP 响应头单独记录在 `read_method.response_media_type`。
6. REPAIR 提出四个错误码：类型错误、commit 不匹配、configuration 不匹配、报告引用不一致。
7. REDUNDANT 由 JSON Schema 和运行时共同拒绝；跨字段 commit/configuration 一致性由运行时检查。
8. GitHub 输出产物通过不可变标签 `e2-contract-v1` 读取，并用 SHA-256 校验。

## Alternatives

### 同时保留 configuration 和 environment

拒绝。两份信息可能发生漂移，消费者无法判断哪一份是权威值。

### 只传 finding_id

该方案减少重复，但 MDFixer 在下载报告前无法完成任何预检。本方案保留小型 finding 摘要，并要求运行时与报告内容核对。

### 所有拒绝都使用 REQUEST_1001

该方案兼容 A06 当前错误枚举，但无法快速区分修复领域中的三种拒绝原因。暂以专用错误码作为提案，等待 A06 决定。

### 使用 main 分支 Raw URL

拒绝。分支内容可变，无法保证另一组日后读取到相同产物。

## Consequences

- 有效请求只有一处 configuration 权威值。
- 样例可通过结构校验和语义校验重复验收。
- 合并后必须创建并推送 `e2-contract-v1` 标签。
- A06 需要确认错误码，并解决 `declaration_location` 与其公共 Schema 不一致的问题。
- 如 A06 修改字段，双方必须同步更新 Schema、样例、ADR 和校验记录。
