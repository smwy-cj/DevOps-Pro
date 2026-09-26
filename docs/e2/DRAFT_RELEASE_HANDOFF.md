# E2 DRAFT v3 发布交接

## 合入前

1. 以远端 `dev` 提交 `95ebe37e984ccdbc872a82fa3eef4d86025a1945` 为基准应用本次补丁。
2. 运行 `python3 scripts/validate-contract.py --skip-remote`，要求 `30/30 checks passed`。
3. 在 PowerShell 7 运行 `pwsh -File scripts/validate-contract.ps1 -SkipRemote`，要求全部通过。
4. 复核 `git diff --check`，确认 REPAIR 样例仍通过。
5. 运行 `python3 scripts/verify-anonymous-image-pull.py`，确认 manifest、config 和全部镜像层可匿名取得。

## 远端分支核对

2026-09-26 核对结果：

- `member3/e2-draft-contract-v2` 的远端 tip 仍为 `4833146a9142a1ae1e59f559748cde726f4348d0`；报告的 `0ff055a796649b1c1711e8ee8c689a89af477217` 尚未出现在 GitHub。庄子宣需先确认推送，或由集成补丁提供等价的 Schema/JSON 修订。
- `integration/draft-artifact-delivery` 的真实远端 tip 为 `2f736cae031bfa9c941a0f76f50920137a16a477`。报告的 `2f736ca6f7f7a1e7b4c6a3d8c8f4e8c1d9c7b6a5` 不是远端提交。
- 已发布的 `e2-draft-contract-v2` 仍含旧 DRAFT JSON，不能移动或作为复评版本使用。

## 发布

1. 将验证后的修改合入并推送至 `dev`。
2. 记录新的完整提交 SHA。
3. 在该提交创建新的附注标签 `e2-draft-contract-v3` 并推送。
4. 不得移动或覆盖 `e2-contract-v1`、`e2-draft-contract-v2`。

示例命令：

```sh
git tag -a e2-draft-contract-v3 -m "E2 DRAFT contract v3"
git push origin e2-draft-contract-v3
```

## 发布后

1. 运行不带 `--skip-remote` 的 Python 校验，要求 `37/37 checks passed`。
2. 在 PowerShell 7 运行完整校验并保存输出。
3. 匿名打开三份 DRAFT JSON、五份 Artifact Raw URL。
4. 执行 `docker manifest inspect --verbose` 检查 GHCR digest 和 `linux/amd64` 平台；有 Docker daemon 的环境再执行匿名 pull/run。
5. 将新标签、完整提交 SHA、校验输出和镜像 digest 发给 A06 复评。

当前 `e2-draft-contract-v2` 指向的版本仍含旧的 DRAFT JSON，不能作为修订完成的证据，也不能重新指向其他提交。

负责人：崔杰负责最终合并和标签；庄子宣负责 Schema/JSON；屠育玮负责验证和交接文档；朱钱晨负责 REPAIR 回归和 A06 联络。
