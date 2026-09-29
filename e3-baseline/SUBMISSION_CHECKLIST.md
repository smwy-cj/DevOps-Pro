# E3 提交检查清单

- [x] 从固定基线 `acd0e268c104d2211b7e5ca821789cfb4c31cfec` 创建文档分支。
- [x] 在全新克隆和干净工作区中完成独立验证。
- [x] DRAFT 本地构建输出 `hello E3`。
- [x] 修复前 MDFixer 行为为 `1 -> 1 -> clean 2`。
- [x] 四份 `reference.patch` 均通过 `git apply --check`，修复后修改头文件可输出 `3`。
- [x] 无效候选构建失败，恢复 `Makefile.before` 后可再次构建并输出 `1`。
- [x] 复现步骤见 `README.md`，命令和原始输出见 `evidence/fresh-clone-validation.txt`。
- [x] 团队分工见 `TEAM_CONTRIBUTIONS.md`。
- [x] 推送分支并创建 Pull Request。

提交分支：`member4/e3-reproducibility-docs`  
Pull Request 目标分支：`e3/b06-test-baseline`  
最终提交 SHA：待推送后填写  
Pull Request 链接：待创建后填写
