# 演示用静态数据（供 GitHub Pages 部署）

本目录**可选**。由以下命令生成：

```bash
python scripts/sync_frontend_data.py
python scripts/prepare_pages_data.py --max-plays 24
```

生成后 `git add deploy/pages-data` 并 push，GitHub Actions 会将其打包进 Pages 站点。

全量数据约 400MB，不宜提交；此处仅保留少量剧本用于在线演示。
