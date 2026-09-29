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

## Docker 证据复现

从仓库根目录执行下列命令，需要可用的 Docker daemon。失败样本的退出码必须非零，参考镜像构建和运行的退出码必须为 0，运行日志必须严格等于一行 `hello E3`（含结尾换行）。

```bash
cd e3-baseline/draft/project
mkdir -p ../logs
docker build --no-cache --progress=plain -f ../Dockerfile.broken -t e3-draft-broken . > ../logs/broken-build.log 2>&1
printf '%s\n' "$?" > ../logs/broken-exit-code.txt
docker build --no-cache --progress=plain -f ../Dockerfile.reference -t e3-draft-reference . > ../logs/reference-build.log 2>&1
build_result=$?
docker image inspect --format '{{.Id}}' e3-draft-reference > ../logs/image-id.txt
docker run --rm e3-draft-reference > ../logs/reference-run.log 2>&1
run_result=$?
printf 'build=%s\nrun=%s\n' "$build_result" "$run_result" > ../logs/reference-exit-codes.txt
printf 'hello E3\n' | cmp -s - ../logs/reference-run.log
```

没有本地 Docker 时，`.github/workflows/e3-draft-docker-evidence.yml` 在 GitHub 托管的 Ubuntu runner 上执行同样的命令及断言，上传真实证据。将工作流工件中的六个文件复制到 `logs/` 并提交。工作流成功只能说明该次构建通过；镜像 ID 和日志应来自同一次运行。
