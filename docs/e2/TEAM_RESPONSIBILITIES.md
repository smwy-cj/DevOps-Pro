# B06 E2 分工与工作记录

## 成员与职责

| 成员 | 姓名 | 主要职责 | E2 交付 |
|---|---|---|---|
| 组员一 | 崔杰 | 仓库集成与 DRAFT 构建环境 | 维护 `dev`、构建并发布 GHCR 镜像、生成 UTF-8 构建证据、创建不可变标签 |
| 组员二 | 朱钱晨 | MDFixer 与 A06 联调 | 复核 REPAIR 契约、维护 MDFixer 语义、与 A06 确认接口和验收结果、协助最终回归 |
| 组员三 | 庄子宣 | 公共 Job Schema 与 DRAFT 契约 | 维护 `task.schema.json`、DRAFT 请求/成功/失败样例和契约字段 |
| 组员四 | 屠育玮 | DRAFT Artifact 验证与交付文档 | 校验 Artifact、编码、哈希、匿名读取和镜像取得，维护验证记录与发布交接 |

## 已完成记录

### 崔杰

- 将 REPAIR 验证分支合入 `dev` 并发布 `e2-contract-v1`。
- 建立 DRAFT GitHub Actions 构建流程，将参考镜像发布到 GHCR。
- 生成失败构建、成功构建、运行以及匿名拉取/运行证据。
- 固定镜像 digest：`sha256:b2dbfef36913f7322287f155650cea3f064d2986d414700e916f87404402d2c7`。

### 朱钱晨

- 复核庄子宣提供的 REPAIR 契约和 A06 固定报告。
- 明确 `MANUAL_REFERENCE`、`recheck: NOT_RUN`、路径基准和修复声明风格。
- 完成 A06/B06 REPAIR 接受确认与后续沟通。
- 协助屠育玮独立取得并校验全部 GHCR 镜像 blob。

### 庄子宣

- 负责 REPAIR 与 DRAFT 的公共 Job Schema 和专项 JSON 契约。
- DRAFT v3 要求包括 `schema_version: 1.0.0`、幂等键、输入回显、configuration、标准错误码和 Artifact 引用。

### 屠育玮

- 整理 DRAFT Artifact 交付规则、验证脚本和发布文档。
- 完成镜像匿名 Registry 拉取验证：取得 manifest、config 和六层镜像 blob，共 `98,951,002` 字节，全部 digest 和大小匹配。
- 保存验证证据到 `docs/e2/evidence/draft-v3-anonymous-image-pull.txt`。

## 记录原则

- 工作记录按实际负责人署名；协助执行单独注明。
- `AI_USAGE.md` 记录实际使用 AI 的人和任务，不把其他成员的工作冒充为自己的 AI 使用。
- 已发布标签不可移动；新修订通过新标签交付。
