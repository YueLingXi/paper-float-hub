# Paper Float Hub

Paper Float Hub 是论文数据生成端，适合部署在 GitHub 仓库中。它会通过 GitHub Actions 定时从 arXiv OAI-PMH 拉取最近论文，按关键词配置评分，尝试匹配 CCF 等级，然后把结果发布为 `public/latest.json`，供桌面端读取。

## 在哪里修改查询关键词

主要修改这里：

```text
config/profiles.yml
```

常用字段说明：

- `include_keywords`：想关注的关键词。标题命中加 3 分，摘要命中加 2 分。
- `exclude_keywords`：不想看到的关键词。标题或摘要命中后直接丢弃。
- `arxiv_categories`：关注的 arXiv 分类，例如 `cs.AI`、`cs.CL`、`cs.CV`。
- `ccf_levels`：允许保留的 CCF 等级，例如 `[A, B]`。
- `score_threshold`：最低入选分数，默认示例为 `3`。

修改后提交到 GitHub，GitHub Actions 下一次运行时会生成新的 `public/latest.json`。

## 本地运行

```bash
pip install -r requirements.txt
python src/main.py
```

生成文件：

- `public/latest.json`：桌面端默认读取的最新结果
- `public/papers/YYYY-MM-DD.json`：每日历史归档
- `rank/ccf.json`：自动下载或降级缓存的 CCF 数据

## 部署到 GitHub

1. 新建 GitHub 仓库，例如 `paper-float-hub`。
2. 把本目录内容推送到仓库。
3. 在仓库 Settings -> Pages 中启用 GitHub Pages。
4. Actions 会每天 UTC 02:00 自动运行，也可以手动执行 `Daily Paper Feed`。
5. 桌面端的订阅地址填写：

```text
https://你的用户名.github.io/paper-float-hub/latest.json
```