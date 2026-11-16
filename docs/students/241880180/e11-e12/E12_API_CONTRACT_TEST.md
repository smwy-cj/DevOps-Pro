# E12 API 契约测试：幂等键冲突

负责成员：屠育玮（241880180）

## 场景

向 `POST /v1/jobs` 提交两份请求。两份请求使用相同的 `idempotency_key`，但 `input.target` 分别为不同的完整提交标识。

## 预期与结果

- 首次请求创建一个任务，返回 HTTP `202` 和 `job_id`。
- 第二次请求不得复用或新建任务，返回 HTTP `409` 和 `{"error":"IDEMPOTENCY_CONFLICT"}`。
- 服务端任务数量保持为 1。

测试 `Student241880180E12Tests.test_same_key_different_target_returns_idempotency_conflict` 已实际通过。

## 证据

测试在运行时写入以下目录，供本地归档和 CI artifact 保留：

`work/241880180-e12-idempotency-conflict/`

- `first-request.json` 与 `first-response.json`
- `conflict-request.json` 与 `conflict-response.json`
- `test.log`
