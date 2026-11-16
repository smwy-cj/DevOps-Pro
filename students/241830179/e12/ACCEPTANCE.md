# 241830179 E12 本地 Linux/Docker 验收

2026-11-13 已在本机 Ubuntu 24.04 / WSL2 / Docker Engine 29.7.2 完成 E12
全流程及独立复验。正式任务 `job-c27b70783daa47a9a8ef99b739f3c78a` 返回
`SUCCEEDED`，交付摘要为 `VERIFIED`。

## 仓库与版本

| 内容 | 固定值 |
|---|---|
| 仓库 | https://github.com/smwy-cj/DevOps-Pro.git |
| 个人分支 | `student/241830179/e12-real-project` |
| PR | https://github.com/smwy-cj/DevOps-Pro/pull/17 |
| 被测目录 | `e3-baseline/mdfixer/fixed-input` |
| 基线完整 SHA | `37ecb07a11cbc937da8f847e96dbb94d8d0eb6e1` |
| 目标完整 SHA | `71ae2ffc4ce9fa99734c297f44c6e057f0df03cf` |
| 本次执行工具 SHA | `6d00c9b557435bf44a598c10f4848cf19ee143cc` |
| 原项目来源 SHA | `be73686c6a9fdbb7c4d3eadb45779233afa33083` |

项目复用本组 E3 分支的简单 C/Make 课程项目，目标增加 --double、非法参数处理及
三项功能测试。既有缺失依赖保留在被测目标提交中，由本次实时报告驱动修复。
本分支已应用经独立复验的修复；复现请求继续固定引用上述修复前目标 SHA。

## 实测结果

| 检查 | 实测结果 |
|---|---|
| Linux 容器测试 | 24/24 通过 |
| DRAFT 首轮 | 构建退出码 1，实际复现 `MISSING_MAKE` |
| DRAFT 候选 | 构建退出码 0，容器运行退出码 0，输出 `1` |
| 基线全量检测 | 1 条 MISSING：`main.o -> config.h` |
| 目标增量与目标全量 | 同一条 MISSING，比较一致 |
| 修复 | `main.o: main.c` 增加 `config.h` 声明 |
| 修复验证 | 补丁应用、构建、功能测试、头文件触发重建及变更后测试全部通过 |
| 修复后全量检测 | MISSING 为 0 |
| 干净检出独立复验 | `SUCCEEDED`，全量检测 MISSING 为 0 |
| 产物完整性 | 原结果清单中的 385 个产物全部通过 SHA-256 和字节数校验 |

验证副本将 VALUE 从 1 改为 2 后，普通 make 重建 main.o，三项功能测试通过，
普通输出为 2、--double 输出为 4。头文件变更保留在验证副本中，原目标副本头文件
保持初始值。增量检测采用保守刷新，本次不报告性能收益。

HTTP 提交使用 `POST /v1/jobs`，返回 202，随后轮询终态、下载产物并校验完整性。
本机服务只映射到 `127.0.0.1:18080`，验收后已停止本次服务容器。

## 运行修复与环境记录

首次完整请求因 Debian HTTP 软件包下载失败而返回 `DRAFT_FAILED`；原始失败结果
和日志已保留。候选 Dockerfile 改用可达的 HTTPS 镜像源，保留软件源签名校验，
安装 gcc/make/libc6-dev。准备入口将候选文件 SHA-256 写入请求，内容变化会产生
不同幂等键；执行器在使用候选前再次检查该哈希。新增回归测试已通过。

服务镜像 ID：
`sha256:5e6856676a0fa8aa7525ccc31f1001b44cdcdbdc8af2d746357f61e917fa90ea`。
候选 Dockerfile SHA-256：
`751d9b48821b96bb3ac899293871030299b599b274f2781c5e0dca59a0778587`。
实际工具版本见 `toolchain.lock`，其中 Make 4.4.1、strace 6.13、Python 3.13.14；
基础镜像按摘要固定，apt 软件包版本由本次锁定记录保存。

## 证据

以下文件位于 [acceptance/2026-11-13/](acceptance/2026-11-13/)：

- [实际请求](acceptance/2026-11-13/request.json)、[HTTP 请求](acceptance/2026-11-13/api-request.json)、[提交响应](acceptance/2026-11-13/submit-response.json)
- [result.json](acceptance/2026-11-13/result.json)、[实际补丁](acceptance/2026-11-13/candidate.patch)
- [首次修复验证](acceptance/2026-11-13/validation.json)、[独立复验](acceptance/2026-11-13/reverification.json)
- [最终全量检测](acceptance/2026-11-13/final-findings.json)、[独立全量检测](acceptance/2026-11-13/independent-final-findings.json)
- [完整性审计](acceptance/2026-11-13/acceptance-audit.json)、[交付结论](acceptance/2026-11-13/delivery-summary.json)
- [完整原始归档](acceptance/2026-11-13/full-evidence.tar.gz)、[导出文件校验清单](acceptance/2026-11-13/files.sha256.json)

归档为 729055 字节，SHA-256：
`220ca7a45b4eb4c569752a7d773f29785ebe1c63c56202c0619c58ba1b639af1`。
归档包含成功任务、独立复验、构建/测试/系统日志、失败尝试及执行前的准备材料。
归档中的执行前状态文件是当时快照，正式结论以 result、reverification 和
delivery-summary 为准。外层导出文件保持原始内容，原结果清单引用的全部文件
可在完整归档中按原路径找到。

项目适配仍限定为单层 GNU Make、显式对象规则、本地 C/头文件。该项目来源为本组
课程项目；报告保留此范围，不扩展为外部生产项目或论文工具的效果结论。
