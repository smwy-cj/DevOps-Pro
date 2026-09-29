# B06 E3 DRAFT 测试基线

## 项目输入

项目位于 project/，构建命令为 make clean 和 make，验证命令为 ./hello。
预期退出码为 0，标准输出严格等于 hello E3。

## 失败候选

文件：Dockerfile.broken
预期 Docker 构建退出码非 0，日志应能定位到缺少 make 或 C 工具链。
失败日志保存为 logs/broken-build.log。

## 参考成功候选

文件：Dockerfile.reference
预期镜像构建成功，容器运行退出码为 0，输出严格等于 hello E3。
保存构建日志、运行日志和镜像 ID。

## 已完成证据

macOS 主机构建和运行记录保存在 logs/host-build.log、logs/host-run.log 和 logs/host-exit-codes.txt。
Docker 证据由具有 Docker daemon 的 Linux 或 GitHub Actions 环境生成。
