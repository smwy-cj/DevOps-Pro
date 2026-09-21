# AI_USAGE.md 追加条目

## 2026-09-21：E2 公共 Schema 与 REPAIR 联调样例

- 工具/模型：OpenAI Codex。
- 任务：核对 A06 报告与 B06 REPAIR 请求的公共字段，生成 Schema、成功/拒绝样例、Patch、ADR 和验证脚本。
- AI 建议：增加 `idempotency_key`；将重复的 configuration/environment 合并为单一 configuration；区分 Artifact 逻辑 media type 与 HTTP Content-Type；使用不可变标签和 SHA-256；为 REPAIR 拒绝原因提出专用错误码。
- 人工判断：接受幂等键、单一 configuration、路径基准、内容校验和可复现样例；REPAIR 专用错误码及 `declaration_location` 的最终处理等待 A06 确认，未冒充双方已达成决定。
- 人工验证：在 Ubuntu 22.04 on WSL2、GNU Make 4.3、GCC 11.4.0 上应用 Patch。修改 `config.h` 后运行普通 `make`，确认 `main.o` 被重编且程序输出从 1 更新为 2。运行 `scripts/validate-contract.ps1`，20 项检查通过。
- 关联文件：`contracts/schemas/task.schema.json`、`contracts/examples/repair/`、`contracts/artifacts/a06-b06/`、`docs/e2/adr/0001-repair-contract.md`、`scripts/validate-contract.ps1`。
