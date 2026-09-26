# A06/B06 E2 REPAIR 联调验收记录

## 1. 验收结论

A06 与 B06 已完成 E2 REPAIR 联调，双方按 `e2-contract-v1` 固定基线完成接口、产物读取、错误码和完整性校验。联调结果通过，记录确认日期为 **2026-09-23**。

本记录验收的是 A06 的 MISSING 报告与 B06 的 REPAIR 契约样例、修复产物和验证证据之间的一致性；它不表示 MDFixer 服务或 BuildChecker 检测器已经部署运行。

## 2. 接口与基线确认

- A06 接受 `input.configuration` 和 `input.finding`，并按固定报告内容进行一致性校验。
- A06 接受 REPAIR 错误码 `REPAIR_7001` 至 `REPAIR_7004`。
- `e2-contract-v1` 是 A06 与 B06 双方确认的固定契约基线。
- 联调涉及的全部文件均支持匿名读取；读取后按 UTF-8 解码，并按对应逻辑格式解析和校验。
- A06 被测源码固定为提交 `f104b5bc7f4044a119d1b46aab5d64e70cf89de8`；B06 的 REPAIR 请求、Patch 和修复报告均引用该提交及同一构建配置 `gcc-11.4.0-O0-ubuntu22.04-amd64`。

## 3. 联调证据

| 证据 | 位置或读取方式 | 说明 |
|---|---|---|
| A06 ERROR_REPORT | 请求中的 `input.error_report.read_method.url` | 匿名 HTTPS GET；HTTP 响应按 UTF-8 解码为 JSON，并校验状态、媒体类型、大小和 SHA-256。 |
| B06 REPAIR 请求与结果 | `contracts/examples/repair/` | 包含有效请求、成功结果以及 REDUNDANT、commit 不匹配、configuration 不匹配的拒绝样例。 |
| Patch | `contracts/artifacts/a06-b06/fix-main-o-config-h.patch` | 将 `config.h` 加入 `main.o` 的显式依赖。 |
| 修复报告与构建日志 | `contracts/artifacts/a06-b06/repair-report.json`、`contracts/artifacts/a06-b06/repair-verification.txt` | 记录修复原因、产物完整性元数据、clean build 和增量重建行为。 |

## 4. 校验结果

| 校验方 | 校验范围 | 结果 |
|---|---|---:|
| B06 | 契约与联调校验 | **21/21** |
| A06 | 独立校验 | **21/21** |
| A06 | 联网语义与完整性校验 | **22/22** |

B06 校验可通过以下命令复现；校验覆盖 Schema、四类请求语义、三类拒绝响应、产物 SHA-256/大小、成功结果与修复报告一致性，以及 A06 匿名报告读取和内容一致性。

```powershell
python scripts/validate-contract.py
pwsh -File .\scripts\validate-contract.ps1
```

A06 的 `21/21` 与 `22/22` 是 A06 已确认并提供给本次验收的结果；B06 不将其表述为自身执行的 A06 校验。

## 5. Patch 实际验证

Patch 已在双方约定的固定提交上实际应用并验证通过。验证通过 `scripts/verify-patch.sh <a06-repository-path> <patch-path>` 复现，覆盖补丁可应用性、源码修改结果以及以下行为：

1. clean build 后程序输出初始值 `1`；
2. 将 `config.h` 中的 `VALUE` 改为 `2` 后，普通 `make` 重建 `main.o`，程序输出 `2`；
3. clean build 后程序仍输出 `2`。

该结论基于固定提交上的实际构建行为，不仅是 Schema 或静态样例校验。检测器重检状态仍为 `NOT_RUN`，原因是 BuildChecker 尚未实现。

## 6. 换行符约定

A06 提议的 `*.sh text eol=lf` 规则已完成落地，完成提交为 `0d3b40961807ece5cb8e6d77f4de34c3f03e8317`。该规则用于保持 Shell 脚本在不同操作系统工作区中的 LF 换行一致性。

## 7. 确认信息

- A06 确认日期：2026-09-23
- 验收状态：通过
- 记录提交：`4833146a9142a1ae1e59f559748cde726f4348d0`
- 合并提交：`4a8a8c47a50973ffd7d14945b67a0bddef224100`
