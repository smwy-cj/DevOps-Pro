# DevOps-Pro

**DevOps课程项目作业**

**E2任务B组实现：**

-  DRAFT：自动生成并验证Dockerfile
- MDFixer：自动修复Makefile缺失依赖

## E2 状态

- REPAIR：`e2-contract-v1` 已通过 A06/B06 联调验收。
- DRAFT：v3 候选契约已补齐公共 Job Schema、固定镜像和标准 Artifact，等待发布 `e2-draft-contract-v3` 后由 A06 复评。

本地校验：

```sh
python3 -m pip install -r scripts/requirements-validation.txt
python3 scripts/validate-contract.py --skip-remote
```

成员职责和工作记录见 `docs/e2/TEAM_RESPONSIBILITIES.md`。
