# CS3320 京剧剧本可视化

在线演示：push 到 `main` 后由 GitHub Actions 自动部署 Pages（数据为仓库内 `demo-data/` 约 10 部样本）。

## 环境

- Python 3.10+ · Node.js 18+

```bash
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

## 数据准备

将「京剧剧本」压缩包放到 `data/京剧剧本/`。

## 本地全库流程

在项目根目录：

```bash
# 1. 预处理 → artifacts/cleaned/
python backend/preprocessing/run_pipeline.py --config configs/pipeline.yaml

# 2. 分析 → artifacts/analytics/
python backend/analytics/run_analytics.py --all

# 3. 同步到前端
rm -rf frontend/public/data
python scripts/sync_frontend_data.py

# 4. 启动
cd frontend && npm run dev
```

## GitHub Pages

```bash
python scripts/build_demo_data.py    # 从 artifacts 裁剪 demo-data/
python scripts/copy_demo_to_public.py
cd frontend && npm run build
git add demo-data/ && git push       # CI 会自动部署
```

## 模块说明

| 目录 | 文档 |
|------|------|
| 预处理 | [backend/preprocessing/README.md](backend/preprocessing/README.md) |
| 分析 | [backend/analytics/README.md](backend/analytics/README.md) |
| 前端 | [frontend/README.md](frontend/README.md) |
| 数据契约 | [schemas/README.md](schemas/README.md) |

## 前端路由

`/` 总览 · `/role` 行当 · `/network` 网络 · `/theme` 主题 · `/narrative` 叙事 · `/integrated` 综合
