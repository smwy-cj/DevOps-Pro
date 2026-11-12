# 241830179 E12 执行与交付

当前状态：前置材料已准备；Linux/Docker 完整流程和独立复验由本人执行。
`result.json`、实际生成的补丁及复验结论由运行产生，不预填成功结果。

## 项目及版本

| 项目 | 固定值 |
|---|---|
| 仓库 | https://github.com/smwy-cj/DevOps-Pro.git |
| 个人分支 | `student/241830179/e12-real-project` |
| 工具起点 | `944b587d0fa469b854acc393a4f9a0c2edc1e5cb` |
| 被测子目录 | `e3-baseline/mdfixer/fixed-input` |
| 基线完整 SHA | `37ecb07a11cbc937da8f847e96dbb94d8d0eb6e1` |
| 目标完整 SHA | `71ae2ffc4ce9fa99734c297f44c6e057f0df03cf` |
| 原项目来源 | `e3/b06-test-baseline`，`be73686c6a9fdbb7c4d3eadb45779233afa33083` |

该项目是本组早期维护的 C/Make 课程项目，程序输出配置整数。基线逐字节恢复原
Makefile、main.c、config.h；目标加入 `--double`、非法参数处理和三项功能测试。
原有 `main.o -> config.h` 缺失依赖保留给检测器发现。项目来源属于课程项目，
报告应保留这一事实；“真实项目”的课程认定需以该来源判断。

其他分支候选：`dev:draft-baseline`、`e3/b06-test-baseline:e3-baseline/draft/project`
及 `e4/b06-reproducible-env:fixtures/draft` 都有简单 C 应用；所选目录同时具有
显式对象规则、头文件和既有缺失依赖，适合完整修复与复验流程。

## 环境

在 Linux 电脑、WSL2 Linux 终端或 SSH 登录后的 Linux 服务器执行。需要 Git、
Python 3.9+、运行中的 Docker Engine，以及当前用户访问 Docker 的权限。
WSL2 可连接 Docker Desktop 的 Linux 引擎。PowerShell 本身不执行完整检测。

运行会构建课程服务镜像，挂载本项目目录与 Docker socket，在隔离副本执行检测和
修复，并创建候选镜像。头文件复验会把副本中的 VALUE 从 1 改为 2，检查 main.o
重建，并验证普通输出为 2、--double 输出为 4。镜像依赖下载需要联网。不要在 Windows 挂载目录中做
跨系统混合编译；WSL2 建议使用 Linux 家目录。

基础镜像摘要固定；apt 软件包版本由仓库解析，完整运行应一并归档
`docker image inspect` 与服务镜像 `/opt/toolchain.lock`。这不等于逐包版本已冻结。

## 一次完整执行

在一个新的工作目录运行，避免覆盖先前证据：

```sh
git clone --branch student/241830179/e12-real-project --single-branch https://github.com/smwy-cj/DevOps-Pro.git DevOps-Pro-e12-241830179
cd DevOps-Pro-e12-241830179
git config --local user.name 241830179
git config --local user.email 196506694+smwy-cj@users.noreply.github.com
python3 scripts/e12_241830179.py prepare
python3 scripts/e12_241830179.py build
python3 scripts/e12_241830179.py test
python3 scripts/e12_241830179.py run
python3 scripts/e12_241830179.py reverify
docker image inspect course-e11e12:241830179 > work/241830179-e12/service-image.json
docker run --rm --network none course-e11e12:241830179 cat /opt/toolchain.lock > work/241830179-e12/toolchain.lock
python3 scripts/e12_241830179.py collect
```

每条命令成功后再执行下一条。`prepare` 只创建本地项目克隆、请求和候选 Dockerfile，
不运行检测器；后面的 `run` 消费本次实际检测报告。基线全量、目标增量、目标全量
对照、修复验证和最终全量复验都会产生独立文件。`reverify` 从目标 SHA 再次检出
干净副本，校验补丁完整性，重新执行应用、构建、测试、头文件触发重建和全量检测。

如果镜像镜像源不可达，可用同一摘要从 Docker Hub 构建服务镜像，再继续 `test`：

```sh
docker build --build-arg BASE_IMAGE=python:3.13-slim@sha256:f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74 -f labs/e11e12/environment/services/buildchecker/Dockerfile -t course-e11e12:241830179 labs/e11e12/environment
```

## 如需验证 HTTP 接口

HTTP 路线与上面的 `run` 二选一，使用新的克隆完成 `prepare/build/test` 后，在第一个终端运行：

```sh
python3 scripts/e12_241830179.py serve
```

第二个终端进入同一仓库，执行：

```sh
python3 scripts/e12_241830179.py api
python3 scripts/e12_241830179.py reverify
python3 scripts/e12_241830179.py collect
```

API 客户端保存 POST 请求与响应、轮询终态、下载结果和产物，并逐项验证 SHA-256
和字节数。服务仅映射到主机 `127.0.0.1:8080`；跨电脑访问时使用 SSH 隧道。

## 验收标准与产物

| 产物 | 路径 |
|---|---|
| 仓库来源、两个项目 SHA | `students/241830179/e12/project.json` |
| 可直接使用的完整请求 | `students/241830179/e12/request.json` |
| 本次实际请求及准备记录 | `data/241830179-e12/` |
| 总结果 | `work/241830179-e12/result.json` |
| DRAFT 两次构建及程序验证 | `work/241830179-e12/draft-build/` |
| 实际检测报告 | `work/241830179-e12/incremental-report.json` |
| 实际生成的补丁 | `work/241830179-e12/candidate.patch` |
| 修复计划与首次验证 | `work/241830179-e12/repair-plan.json`、`validation/validation.json` |
| 最终全量结果 | `work/241830179-e12/final-full/findings.json` |
| 独立复验结论 | `work/241830179-e12-reverify/reverification.json` |
| 交付压缩包、摘要结论 | `work/241830179-e12-delivery/` |

应同时满足：总结果 `SUCCEEDED`；五个阶段 `draft/full-check/incremental-check/repair/recheck`
齐全；修复验证 `accepted=true`；最终全量报告无 MISSING；独立复验 `SUCCEEDED`；
交付摘要为 `VERIFIED`。REDUNDANT 声明保留，不通过删除它们制造成功结果。

本适配范围为单层 GNU Make、显式对象规则和本地 C/头文件；递归 Make、多输出
recipe、软链接、复杂规则等会明确失败。增量检测会保守地在 C/头文件或构建配置
变化时刷新映射对象，不能据此宣称获得增量性能收益。

执行失败时保留 `work/` 与日志，根据 `result.json.error` 定位。不要将网络故障
写成缺少 make；DRAFT 首轮必须实际复现 `MISSING_MAKE`。重跑请使用新的克隆，
不要删除或覆盖旧证据。若只完成部分步骤，交付摘要应保持 `INCOMPLETE`。

本分支推送和 PR 不自动运行继承的 Linux/Docker CI；其他分支行为保留。
需要时可由本人手动触发工作流，其固定样例 CI 成功不能替代本次真实目录的运行。

执行完成后，将生成的 `.tar.gz` 交回当前对话，继续完成产物核查、结果文档和 PR
证据更新。运行前的草稿 PR 只代表准备工作可审查。
