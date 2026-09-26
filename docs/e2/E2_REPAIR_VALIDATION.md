# E2 REPAIR 契约集成校验记录

## 1. 校验结论

组员三庄子宣的 E2 REPAIR 契约成果已应用至独立验证分支，并完成本地校验。

- 验证分支：`integration/e2-repair-validation`
- 庄子宣原始分支：`member3/e2-repair-contract`
- 庄子宣原始提交：`4259d387b280ebd5f460edf964a192e38929c0a8`
- 应用后的提交：`508fbcbb77155dd312bf5b53c4b5717e1dc3a4a4`
- LF 兼容修复提交：`9d055227cf7742ed6e451d7dc679f5590d9da110`
- 校验结果：`All 20 contract checks passed.`
- 校验日期：2026-09-22

## 2. 集成过程

1. 从最新 `dev` 创建 `integration/e2-repair-validation`。
2. 将庄子宣的提交 `4259d38` 通过 `cherry-pick` 应用到验证分支。
3. 使用 `scripts/validate-contract.ps1` 校验 JSON Schema、语义规则、拒绝响应码、本地产物元数据和远端错误报告。
4. 修复 Windows 工作区的换行符兼容问题。
5. 重新运行全部校验，20 项检查全部通过。

## 3. 遇到的问题与处理

### 3.1 PowerShell 版本兼容

Windows PowerShell 5.1 的 `ConvertFrom-Json` 不支持 `-Depth` 参数，无法直接运行校验脚本。

处理方式：安装并使用 PowerShell 7，通过以下命令执行：

```powershell
pwsh -File .\scripts\validate-contract.ps1
```

### 3.2 REPAIR 产物换行符不一致

Windows 的 `core.autocrlf=true` 将三个文本产物检出为 CRLF，导致实际 SHA-256 和文件大小与契约记录不一致。

涉及文件：

- `contracts/artifacts/a06-b06/fix-main-o-config-h.patch`
- `contracts/artifacts/a06-b06/repair-report.json`
- `contracts/artifacts/a06-b06/repair-verification.txt`

修复后文件大小：

| 文件 | 大小 |
|---|---:|
| `fix-main-o-config-h.patch` | 367 B |
| `repair-report.json` | 1777 B |
| `repair-verification.txt` | 826 B |

同时在 `.gitattributes` 中固定 REPAIR 产物使用 LF，避免不同操作系统再次改变文件内容。

## 4. 校验范围

本次通过的 20 项检查覆盖：

- REPAIR 请求及成功结果的 Schema 校验；
- 三类拒绝请求的 Schema 与语义校验；
- 三类拒绝响应码校验；
- 补丁、修复报告和验证日志的 SHA-256 与大小校验；
- 远端 ERROR_REPORT 的 HTTP 状态、媒体类型、SHA-256 与大小校验。

## 5. 最终状态

在提交 `9d055227cf7742ed6e451d7dc679f5590d9da110` 上：

- 全部 20 项契约检查通过；
- 工作区无未提交修改；
- 未修改 `main` 和 `dev`；
- 验证成果保存在 `integration/e2-repair-validation` 分支。

## 6. MDFixer 负责人补充复核（2026-09-22）

以上 20 项是崔杰在提交 `9d055227cf7742ed6e451d7dc679f5590d9da110` 上完成的历史记录。此后，MDFixer 负责人朱钱晨基于集成分支提交 `357df1612bc9870c4e9fcb9a85a8da776e43b94f` 补充了成功结果的来源与重检状态、Makefile 声明风格、项目路径基准，并新增跨平台校验脚本。本节记录的是**本地待合入文件**，不表示已有新的 GitHub 提交。

在仓库根目录安装 Python 3 依赖并执行：

```sh
python3 -m pip install -r scripts/requirements-validation.txt
python3 scripts/validate-contract.py
```

本地结果：`21/21 checks passed`。新增的一项检查确认成功结果与修复报告的来源、检测器重检状态、源码提交及配置一致。远端检查还会下载 A06 固定 ERROR_REPORT，核对 HTTP 状态、媒体类型、字节数、SHA-256，以及请求中选取的 repository、configuration 和 finding。没有网络时可以使用 `--skip-remote`；这时应为 `20/20 checks passed`，不代表完成远端联调。

另外，已针对 A06 固定源码中的 Makefile 执行 `git apply --check`，补丁可应用。先前 Ubuntu 22.04 / Make 4.3 / GCC 11.4.0 的实际构建行为记录仍见三个 REPAIR 产物；本次补充复核没有重新运行这些环境中的构建测试，也没有运行 MDFixer 服务或 BuildChecker 检测器。

合入前还需在 PowerShell 7 环境重跑 `scripts/validate-contract.ps1`。合入并确认文件内容后创建、推送 `e2-contract-v1` 标签；标签发布前，成功结果中的 GitHub Raw 产物地址不可用。
