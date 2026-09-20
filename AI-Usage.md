# AI Usage Record

## 1. 基本信息

- 项目：DevOps-Pro
- 小组：B组
- 任务：DRAFT环境生成与测试基线
- 仓库：https://github.com/smwy-cj/DevOps-Pro
- 工作分支：`dev`
- 基线源码Commit：`3828e6e5e6f7ea27c25b0d627edef9e06b433152`
- 文档整理日期：2026-09-20
- 使用的AI：ChatGPT / Codex

## 2. 任务目标

本任务基于DRAFT论文的基本流程，建立一个可重复运行的Dockerfile生成与修复测试基线：

1. 准备一个可通过GNU Make构建的最小C语言项目；
2. 构造一个缺少构建工具的失败Dockerfile；
3. 运行Docker构建并保存真实失败日志；
4. 根据日志定位缺失依赖；
5. 编写修复后的参考Dockerfile；
6. 验证镜像能够成功构建；
7. 验证容器内程序功能正确；
8. 提供结构化请求、成功响应和失败响应样例；
9. 保存日志、镜像ID和复现说明。

## 3. AI参与内容

AI在本任务中主要提供指导、解释、模板和故障分析，没有代替人工执行本地Docker命令或伪造实验结果。

### 3.1 任务理解与方案拆分

AI协助完成：

- 解释DRAFT的“生成—构建—分析日志—修复—重新验证”流程；
- 区分Dockerfile、镜像和容器；
- 说明构建验证与功能验证的差别；
- 将任务拆分为仓库初始化、最小项目、失败基线、成功基线、接口契约和文档整理等步骤；
- 明确与A组的接口：B组提供可复现构建环境，供A组运行依赖检测工具。

### 3.2 Git与分支管理指导

AI提供了以下操作建议：

- 创建并克隆GitHub仓库；
- 使用`feat/draft-baseline`进行功能开发；
- 解释README只存在于功能分支而未进入`main`的原因；
- 指导提交、推送和获取完整Commit SHA；
- 解释`.gitignore`导致`Makefile`和`*.log`未被跟踪的问题；
- 使用`git add -f`补充必要实验文件；
- 使用`git commit --amend`修改提交说明；
- 根据用户要求创建并推送`dev`分支，保持`main`不变。

### 3.3 最小测试项目设计

AI建议并解释了以下文件：

- `draft-baseline/src/hello.c`：输出`hello E3`的最小C语言程序；
- `draft-baseline/Makefile`：使用GCC编译程序，并提供`clean`目标；
- `draft-baseline/README.md`：记录依赖、构建命令、验证命令和预期输出。

用户在本地创建文件并执行验证。

### 3.4 失败Dockerfile设计

AI建议创建`Dockerfile.broken`，使用`debian:bookworm-slim`作为基础镜像，但不安装GNU Make和GCC，然后执行：

```dockerfile
RUN make
```

实验得到预期错误：

```text
/bin/sh: 1: make: not found
exit code: 127
```

AI解释：退出码127表示命令不存在，该日志可以作为DRAFT修复流程的输入。

### 3.5 构建故障排查

第一次构建没有出现预期的`make: not found`，而是在拉取Debian镜像时失败。AI读取用户提供的日志后定位到：

```text
failed to fetch oauth token
connection attempt failed
```

AI判断这是Docker Hub认证服务的网络连接问题，而不是Dockerfile语法问题，并建议：

1. 单独执行`docker pull debian:bookworm-slim`；
2. 必要时重启Docker Desktop；
3. 检查VPN、代理或网络；
4. 镜像拉取成功后重新运行构建并覆盖无效日志。

用户重新执行后获得预期的缺少Make错误。

### 3.6 参考Dockerfile修复建议

AI根据错误日志建议在`Dockerfile.reference`中安装：

- `make`
- `gcc`
- `libc6-dev`

并清理APT缓存。用户实际执行Docker构建，日志显示：

```text
gcc -Wall -Wextra src/hello.c -o hello
naming to docker.io/library/draft-reference:latest done
```

AI据此确认镜像构建成功。

### 3.7 功能验证

AI要求不能只验证`docker build`成功，还需要执行：

```bash
docker run --rm draft-reference
```

用户实际运行后得到：

```text
hello E3
```

说明容器启动和程序功能均符合预期。

### 3.8 接口契约设计

AI协助设计以下接口样例：

- `contracts/draft-request.json`
- `contracts/draft-success.json`
- `contracts/draft-failure.json`

主要字段包括：

- `schema_version`
- `job_id`
- `trace_id`
- `job_type`
- `status`
- 仓库地址和完整Commit SHA
- 构建命令与验证命令
- Dockerfile、日志和镜像ID路径
- 构建及验证退出码
- 失败阶段、错误码和错误消息

AI还建议使用`python -m json.tool`检查JSON语法。

### 3.9 复现文档

AI协助完善`draft-baseline/README.md`，记录：

- 固定仓库与Commit；
- 项目目录结构；
- 失败基线执行方法；
- 预期错误；
- 修复方案；
- 成功构建方法；
- 功能验证命令；
- 日志及镜像ID位置；
- DRAFT处理流程。

## 4. 人工完成与验证内容

以下工作由用户实际完成：

- 创建GitHub仓库及分支；
- 创建和修改源码、Makefile、Dockerfile、JSON与README；
- 启动Docker Desktop；
- 拉取Docker镜像；
- 执行失败Docker构建；
- 保存失败日志；
- 执行修复后的Docker构建；
- 保存成功日志；
- 运行容器并核对输出；
- 保存镜像ID；
- 检查Git状态；
- 完成Git提交与推送；
- 创建并推送`dev`分支。

所有实验结论均来自用户实际执行产生的日志，不是由AI虚构。

## 5. 最终产物

### 5.1 测试项目

- `draft-baseline/src/hello.c`
- `draft-baseline/Makefile`
- `draft-baseline/README.md`

### 5.2 Docker基线

- `draft-baseline/Dockerfile.broken`
- `draft-baseline/Dockerfile.reference`

### 5.3 实验证据

- `draft-baseline/artifacts/build-failed.log`
- `draft-baseline/artifacts/build-success.log`
- `draft-baseline/artifacts/run-result.log`
- `draft-baseline/artifacts/image-id.txt`

### 5.4 接口样例

- `contracts/draft-request.json`
- `contracts/draft-success.json`
- `contracts/draft-failure.json`

## 6. 结果判断

当前已经完成“DRAFT环境生成与测试基线”的交付要求：

- [x] 固定仓库和源码版本
- [x] 提供项目源码、Makefile和构建文档
- [x] 提供失败Dockerfile
- [x] 保存真实失败日志
- [x] 根据日志补充缺失依赖
- [x] 提供参考成功Dockerfile
- [x] 镜像构建成功
- [x] 容器功能验证成功
- [x] 保存成功日志和镜像ID
- [x] 提供请求、成功响应和失败响应样例
- [x] 提供完整复现说明
- [x] 成果已推送至`dev`分支，未修改`main`

## 7. 当前范围与后续工作

本阶段完成的是DRAFT的测试基线、接口契约和人工模拟修复闭环，尚未实现以下完整自动化能力：

- 自动读取README并生成初始Dockerfile；
- 调用LLM自动分析构建日志；
- 自动生成多个候选Dockerfile；
- 自动循环构建、选择和修复；
- 将DRAFT封装为异步服务；
- 自动上传或分发Docker镜像；
- 与A组检测服务完成端到端联调。

如果课程当前只要求E2接口契约与E3并行测试基线，则本任务已经完成；如果后续进入DRAFT正式实现阶段，还需要继续开发上述自动化功能。

## 8. AI使用原则

- AI输出仅作为方案、代码模板和排错建议；
- 关键命令均由用户在本地执行；
- 构建结果以真实日志和退出码为准；
- 用户对生成内容进行了人工检查；
- 未将AI输出直接视为未经验证的实验结论；
- 仓库凭据、密钥和其他敏感信息未提供给AI。
