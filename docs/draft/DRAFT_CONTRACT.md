# DRAFT 契约与 Artifact 交付规范

## 1. 范围

DRAFT 根据项目文档和构建日志生成或修复 Dockerfile，并返回可复现的构建结果。本文定义 DRAFT 样例中请求、成功结果、失败结果和 Artifact 的交付格式；REPAIR 契约继续由 `e2-contract-v1` 管理，不在本契约中修改。

固定输入见 `contracts/draft-request.json`，成功和失败结果分别见 `contracts/draft-success.json`、`contracts/draft-failure.json`。

## 2. 固定基线

- 仓库：`https://github.com/smwy-cj/DevOps-Pro`
- DRAFT 源码基线：`3828e6e5e6f7ea27c25b0d627edef9e06b433152`
- 项目目录：`draft-baseline`
- 构建命令：`make`
- 验证命令：`./hello`
- 预期输出：`hello DevOps`
- 发布标签：`draft-contract-v1`

所有 DRAFT Artifact URL 必须指向 `draft-contract-v1` 标签，不使用可变的 `main`、`dev` 或个人分支。

## 3. Artifact 规则

每个 Artifact 必须包含：

- HTTPS Raw URL；
- `authentication: NONE`，可匿名读取；
- 解码后的逻辑 `media_type`；
- UTF-8 编码声明；
- 内容 SHA-256 和 `size_bytes`。

当前 Artifact 包括失败 Dockerfile、失败构建日志、成功 Dockerfile、成功构建日志、运行日志和镜像 digest 文件。日志必须是严格 UTF-8，禁止将 Windows PowerShell 默认 UTF-16LE 输出直接发布。

## 4. 镜像 digest

`draft-baseline/artifacts/image-id.txt` 记录构建日志中的镜像 manifest digest，并且必须与成功结果中的 `output.image.digest` 一致。发布交接还必须补充一个公共容器仓库引用，例如：

```text
registry.example/draft-reference@sha256:<digest>
```

只有在不提供认证的环境中执行 `docker pull <digest-reference>` 成功后，镜像 Artifact 才能标记为 `ANONYMOUS_PULL_VERIFIED`。当前样例保留真实 digest，但公共仓库引用尚未提供，状态为 `RELEASE_BLOCKED`。

## 5. 自动验收

在仓库根目录执行：

```powershell
python scripts/validate-draft.py --skip-remote
```

发布标签已存在且网络可用时执行完整校验：

```powershell
python scripts/validate-draft.py
```

镜像公共引用配置完成后，再执行：

```powershell
$env:DRAFT_IMAGE_REF = "registry.example/draft-reference@sha256:<digest>"
python scripts/validate-draft.py --check-image
```

