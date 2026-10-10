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

## E4 可重复工程环境

B06 使用 DRAFT 服务模板建立可重复构建、测试、冒烟测试和密钥检查环境。

- 服务代码：`services/draft/`
- E3 冒烟样例：`fixtures/draft/`
- 容器配置：`compose.yaml`
- 一键命令：根目录 `Makefile`
- 运行证据：`work/<时间>/`，默认不提交

在 Ubuntu 服务器的个人克隆中运行：

```sh
make doctor
make all
```

详细操作和预期结果见 `docs/e4/B_DRAFT_README.md`。
