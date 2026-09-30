# 如何上传到你自己的 GitHub

本仓库已经是一个完整的 git 仓库（`main` 分支，含提交历史）。上传只需三步。

## 方法一：命令行（推荐）

1. 在 GitHub 网页上新建一个**空**仓库：<https://github.com/new>
   - Repository name：`pol2-dao-governance`（可以改名）
   - **不要**勾选 “Add a README / .gitignore / license”（本仓库已经有了）
2. 在本仓库目录里执行（把 `shentonyan` 换成你的 GitHub 用户名）：

   ```bash
   git remote add origin https://github.com/shentonyan/pol2-dao-governance.git
   git push -u origin main
   ```

3. 刷新 GitHub 页面。Actions 页会自动跑一次测试（`.github/workflows/ci.yml`）。

如果你下载的是 zip 压缩包（不含 `.git`），先初始化：

```bash
cd pol2-dao-governance
git init -b main
git add .
git commit -m "Initial commit: PoL2 x DAO governance lab"
git remote add origin https://github.com/shentonyan/pol2-dao-governance.git
git push -u origin main
```

## 方法二：GitHub Desktop

File → Add local repository → 选择本目录 → Publish repository。

## 上传后建议做的事

- 把 `README.md` 快速开始里的 `shentonyan` 换成真实用户名。
- 在 `CITATION.cff` 里填上你的名字（`authors`）。
- 仓库设置 → About：填写简介，添加 topics，例如 `dao` `ai-governance` `quadratic-voting` `proof-of-love` `naturaldao`。
- 想换许可证（例如和 NaturalDAO 一样用 CC0-1.0）：替换 `LICENSE` 文件，并修改 `pyproject.toml` 与 README 末尾的说明。
