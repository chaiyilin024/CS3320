# CS3320 京剧剧本可视化

## 环境要求

- **Python** 3.10+（Windows 可用 `python` 或 `py`）
- **Node.js** 18+ 与 **npm**
- 在项目根目录执行以下命令（Windows / macOS / Linux 相同）

```bash
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

---

## 准备数据

将「京剧剧本」压缩包放到：

```
data/京剧剧本/
```

---

## 完整流程

在**项目根目录**打开终端，依次执行：

```bash
# 1. 预处理（解析 PDF → artifacts/cleaned/）
python backend/preprocessing/run_pipeline.py --config configs/pipeline.yaml

# 2. 分析（行当 / 网络 / 主题 / 叙事 → artifacts/analytics/）
python backend/analytics/run_analytics.py --all

# 3.清理旧缓存目录
rm -rf frontend/public/data

# 4. 同步数据到前端
python scripts/sync_frontend_data.py

# 5. 启动前端
cd frontend
npm run dev
```

---

## GitHub Pages 在线演示（约 10 部示例剧本）

全库 1473 部体积过大，仓库内提交裁剪后的 **`demo-data/`**（约 2MB），用于公开网页演示。

### 本地预览演示版

```bash
# 若已跑完全库分析，可重新生成 demo-data（可选）
python scripts/build_demo_data.py

# 复制 demo-data → frontend/public/data
cd frontend
npm run prepare-data
npm run dev
```

### 部署到 GitHub Pages

1. 将 `demo-data/` 与代码推送到 GitHub（仓库名假设为 `CS3320`）
2. 仓库 **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**
3. 推送 `main` 分支后，Actions 工作流 `.github/workflows/deploy-pages.yml` 会自动构建并发布
4. 访问：`https://<你的用户名>.github.io/CS3320/`

修改示例剧本列表：编辑 `configs/demo_plays.json` 后执行 `python scripts/build_demo_data.py`，再提交 `demo-data/`。

### 全库本地开发（可选）

```bash
python scripts/sync_frontend_data.py   # 同步全部 artifacts → frontend/public/data
cd frontend && npm run dev
```