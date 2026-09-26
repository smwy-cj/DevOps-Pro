# ADR 0002：DRAFT Artifact 可复现交付

- 状态：Accepted with release gate
- 日期：2026-09-26
- 决策范围：DRAFT；不修改 `e2-contract-v1` REPAIR 基线

## 背景

原 DRAFT 样例使用仓库相对路径表示产物，日志由 Windows PowerShell 生成时为 UTF-16LE，镜像只有本地 `image-id.txt`，无法证明另一台机器可以匿名按 digest 拉取。样例预期输出也与真实运行日志不一致。

## 决策

1. DRAFT 结果中的每个文件 Artifact 使用固定 `draft-contract-v1` 标签下的 HTTPS Raw URL。
2. 每个文件记录逻辑媒体类型、UTF-8 编码、SHA-256、字节数和匿名读取要求。
3. 成功结果单独记录镜像 digest；公共仓库 digest 引用和匿名 `docker pull` 是发布门禁。
4. 自动校验同时检查本地字节、远端 URL、日志 UTF-8、镜像 digest 一致性和 Docker 匿名拉取结果。
5. 真实构建输出 `hello DevOps` 作为契约结果；不再保留错误的 `hello E3` 预期。

## 取舍

Git Raw 文件可以匿名、不可变地交付文件产物，但不能替代容器镜像仓库。因此镜像 digest 目前只记录构建证据；在配置公共容器仓库并通过 `docker pull` 前，DRAFT 发布不能标记为完全通过。

