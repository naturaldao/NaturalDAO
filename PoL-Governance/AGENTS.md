# Agent 协作入口

目标：实现 [SPEC](SPEC.md)，用共同数据与评估比较不同方法。

1. 从 [TASKS.md](TASKS.md) 选编号。先 `git fetch origin`，再运行 `python tools/board.py` 查看远端任务，避免撞单。
2. 从公共基线新建 `pol/<任务ID>/<短名>` 分支，复制 [模板](tasks/TEMPLATE.md) 到 `tasks/<任务ID>-<短名>.md`，填写领取人与改动范围，然后推送。**远端分支与任务页就是领取记录**，不需要 PR。
3. 持续把进度、阻塞、结果和交流写入该任务页并推送。协作留言可在任务分支提交只改任务页的 commit；先拉取，不强推覆盖他人记录。暂停或交接也写这里。
4. 完成后跑 `uv run --no-project --offline python tools/check.py`，在任务页写证据和未测项，标为“待集成”。准备纳入公共基线时再开 PR；日常实验不要求 PR。

只改本任务文件，保留他人修改；不提交秘密、私有/保留集或大权重。方法自由，数据版本、划分和评估口径公开一致。没有实测就写“未测”，不把助手标签当人工审定。

默认可信成员有仓库写权限，直接开分支，不必 fork。无写权限者可在自己仓库沿用同一结构，通过结果链接参与。跨仓库结果在 [results](results/README.md) 登记。不要为日常协作直接推主分支。

最小示例（将 yourname 改为自己的短名，在已有本目录的公共基线上执行）：

```sh
git switch -c pol/DATA-01/yourname
# 复制任务模板到 tasks/DATA-01-yourname.md，填写领取信息
git add tasks/DATA-01-yourname.md
git commit -m "Claim DATA-01: independent annotation"
git push -u origin pol/DATA-01/yourname
```

提交前检查暂存内容，只纳入自己这次的文件；任务页路径以本目录为基准。
