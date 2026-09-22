# AI_USAGE.md 追加条目

## 2026-09-21：E2 公共 Schema 与 REPAIR 联调样例

- 工具/模型：OpenAI Codex。
- 任务：核对 A06 报告与 B06 REPAIR 请求的公共字段，生成 Schema、成功/拒绝样例、Patch、ADR 和验证脚本。
- AI 建议：增加 `idempotency_key`；将重复的 configuration/environment 合并为单一 configuration；区分 Artifact 逻辑 media type 与 HTTP Content-Type；使用不可变标签和 SHA-256；为 REPAIR 拒绝原因提出专用错误码。
- 人工判断：接受幂等键、单一 configuration、路径基准、内容校验和可复现样例；REPAIR 专用错误码及 `declaration_location` 的最终处理等待 A06 确认，未冒充双方已达成决定。
- 人工验证：在 Ubuntu 22.04 on WSL2、GNU Make 4.3、GCC 11.4.0 上应用 Patch。修改 `config.h` 后运行普通 `make`，确认 `main.o` 被重编且程序输出从 1 更新为 2。运行 `scripts/validate-contract.ps1`，20 项检查通过。
- 关联文件：`contracts/schemas/task.schema.json`、`contracts/examples/repair/`、`contracts/artifacts/a06-b06/`、`docs/e2/adr/0001-repair-contract.md`、`scripts/validate-contract.ps1`。

## 2026-09-22：MDFixer 负责人复核成功结果

- 工具/模型：OpenAI Codex。
- 任务：复核成员 3 的 REPAIR 契约包与 A06 固定报告的一致性，补充修复结果的可追溯字段。
- AI 建议：在修复报告中记录 `TARGET` 声明风格及理由；将人工实测的补丁标为 `MANUAL_REFERENCE`；把尚未运行的检测器重检明确写成 `NOT_RUN`；说明 Git Patch 与 JSON 项目路径使用不同的基准。
- 待人工复核：AI 核对出 `input.configuration` 与 A06 报告同形，`input.finding` 与目标发现逐项一致，并建议保留补丁和增量构建的人工证据。MDFixer 负责人应确认这些结论后采纳；样例不表示 MDFixer 服务或检测器已运行。
- 验证：核对 A06 报告 SHA-256 与大小、修复产物 SHA-256 与大小，并对 A06 固定 Makefile 执行 `git apply --check`。使用 Python `jsonschema` Draft 2020-12 校验九份请求、响应和报告样例，连同语义、产物及远端报告检查共 21/21 项通过；待组员在 PowerShell 7 环境重跑 `scripts/validate-contract.ps1` 并记录结果。
- 关联文件：`contracts/schemas/task.schema.json`、`contracts/examples/repair/repair-result-success.json`、`contracts/artifacts/a06-b06/repair-report.json`、`docs/e2/REPAIR_CONTRACT.md`、`docs/e2/adr/0001-repair-contract.md`、`scripts/validate-contract.ps1`、`scripts/validate-contract.py`。
