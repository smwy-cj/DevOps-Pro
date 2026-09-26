# ADR 0002：DRAFT v3 契约和交付方式

- 状态：B06 已决定，等待 A06 复评
- 日期：2026-09-26
- 触发评审：A06 提交 `723c0e856897979f896cd3f3505de62bc56a0842`

## 决定

1. DRAFT 沿用公共 `1.0.0` 异步 Job 外壳，专项输入和输出纳入 `contracts/schemas/task.schema.json`。
2. 源码、请求、结果和日志的功能输出统一为 `hello DevOps`。
3. 镜像通过公共 GHCR 交付，并在结果中使用带 `sha256` digest 的完整引用。可变标签不作为联调输入。
4. DRAFT 的成功结果回显固定源码提交和 configuration，命令全部使用 argv 数组。
5. Dockerfile、构建日志和运行日志使用可匿名读取、可校验的 Artifact 引用；文本编码固定为 UTF-8。
6. `ENV_3002` 表示生成环境或镜像构建失败，替代旧样例中不属于公共错误模型的 `COMMAND_NOT_FOUND`。
7. `e2-contract-v1` 继续固定已接受的 REPAIR 基线；已发布但不满足公共 DRAFT Schema 的 `e2-draft-contract-v2` 不移动。修订版使用新标签 `e2-draft-contract-v3`。

## 理由

这些字段允许 A06 将 DRAFT 输出无歧义映射到 FULL_CHECK 的仓库、运行环境和构建命令，并在执行前验证 Artifact 与镜像身份。

## 后果

- 发布前可以运行 30 项离线校验。
- 发布 `e2-draft-contract-v3` 后必须运行包含 Raw Artifact 和镜像清单的联网校验，再请求 A06 复评。
- 后续修改 Artifact 内容会改变 SHA-256，必须同步更新 JSON；不可移动已经交付的标签。
