# E3 可复现性基线

## 范围与固定基线

本目录记录 E3 的本地复现、MDFixer 修复和拒绝候选验证。所有结果以
`e3/b06-test-baseline` 的固定提交
`acd0e268c104d2211b7e5ca821789cfb4c31cfec` 为准；复现前必须检出该提交，
避免后续分支改动影响结论。

目录说明：

- `draft/`：DRAFT 的本地 C 项目、Dockerfile 和预期结果。
- `mdfixer/`：修复前输入、四种参考修复风格及无效候选。
- `evidence/fresh-clone-validation.txt`：在全新克隆中实际执行的命令和输出。

基线采集环境见 `environment.txt`（macOS arm64、GNU Make 3.81、Apple clang）。
本次独立验证在 Windows AMD64 上完成，使用 Git 2.42.0.windows.2、GNU Make
4.4.1 和 MinGW-W64 GCC 12.3.0。因此记录同时覆盖了不同操作系统下的可复现性。

## 前置条件

需要 `git`、GNU Make 和 C 编译器。Windows 的验证命令使用 Git for Windows 的
`rm` 与 MinGW 工具链：

```powershell
$env:Path = 'C:\Program Files\Git\usr\bin;C:\mingw64\bin;' + $env:Path
```

其他环境可将下文的 `mingw32-make` 替换为 `make`。

## DRAFT 本地构建

在仓库根目录执行：

```powershell
mingw32-make -C e3-baseline/draft/project clean
mingw32-make -C e3-baseline/draft/project
& e3-baseline/draft/project/hello.exe
```

预期输出为 `hello E3`。本任务要求的是本地 DRAFT 构建；Docker 不是该检查的前置条件。

## MDFixer 修复前行为

`fixed-input/` 的 Makefile 未声明 `config.h` 是 `main.o` 的依赖。复制修复前的
Makefile，将 `config.h` 中的 `VALUE 1` 改成 `VALUE 2` 后依次执行构建、增量构建和
clean build：

```powershell
Copy-Item e3-baseline/mdfixer/fixed-input/Makefile.before e3-baseline/mdfixer/fixed-input/Makefile -Force
Push-Location e3-baseline/mdfixer/fixed-input
mingw32-make clean; mingw32-make; .\main.exe
(Get-Content config.h) -replace 'VALUE 1', 'VALUE 2' | Set-Content -NoNewline config.h
mingw32-make; .\main.exe
mingw32-make clean; mingw32-make; .\main.exe
Pop-Location
```

预期为 `1 -> 1 -> clean 2`：普通增量构建未重新编译，clean build 才读取新头文件。

## 四种参考修复

`styles/target`、`macro`、`hybrid`、`implicit` 中均提供 `Makefile.before` 和
`reference.patch`。每种风格按以下流程验证：

```powershell
Copy-Item Makefile.before Makefile -Force
git apply --check reference.patch
git apply reference.patch
mingw32-make clean; mingw32-make; .\main.exe
Start-Sleep -Seconds 2
(Get-Content config.h) -replace 'VALUE 1', 'VALUE 3' | Set-Content -NoNewline config.h
mingw32-make; .\main.exe
```

首次输出应为 `1`，修改头文件后普通 `make` 输出应为 `3`。修改前至少等待两秒是验证
条件：部分文件系统和 Make 组合按秒解析时间戳，等待可保证头文件时间晚于已生成目标。

## 无效候选与恢复

在 `mdfixer/invalid-candidate/` 中执行：

```powershell
git apply --check invalid.patch
git apply invalid.patch
mingw32-make clean; mingw32-make
Copy-Item Makefile.before Makefile -Force
mingw32-make clean; mingw32-make; .\main.exe
```

无效候选应以 `No rule to make target 'nonexistent.h'` 失败（退出码 2）。恢复原始
Makefile 后构建成功并输出 `1`。完整实际结果见证据文件。
