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

## macOS / Linux 完整流程

在**项目根目录**打开终端，依次执行：

```bash
# 1. 预处理（解析 PDF → artifacts/cleaned/）
python backend/preprocessing/run_pipeline.py --config configs/pipeline.yaml

# 2. 分析（行当 / 网络 / 主题 / 叙事 → artifacts/analytics/）
python backend/analytics/run_analytics.py --all

# 3. 同步数据到前端
python scripts/sync_frontend_data.py
# 或：bash scripts/sync_frontend_data.sh

# 4. 启动前端
cd frontend
npm run dev
```

浏览器打开终端里显示的本地地址（一般为 `http://localhost:5173`）。

**清理前端旧缓存（可选）**

```bash
rm -rf frontend/public/data
python scripts/sync_frontend_data.py
```

---

## Windows 完整流程

在**项目根目录**打开 **PowerShell**，依次执行：

```powershell
# 1. 预处理
python backend/preprocessing/run_pipeline.py --config configs/pipeline.yaml

# 2. 分析
python backend/analytics/run_analytics.py --all
# 或：powershell -File scripts/run_analytics.ps1 --all

# 3. 同步数据到前端
python scripts/sync_frontend_data.py
# 或：powershell -ExecutionPolicy Bypass -File scripts/sync_frontend_data.ps1

# 4. 启动前端
cd frontend
npm run dev
```

**清理前端旧缓存（可选）**

```powershell
Remove-Item -Recurse -Force frontend\public\data -ErrorAction SilentlyContinue
python scripts/sync_frontend_data.py
```

> 若提示无法运行脚本，可先执行：  
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

---

## 常用可选命令

```bash
# 只聚合全库 global/*.json（已有单剧分析结果时）
python backend/analytics/run_analytics.py --global-only

# 回填主题质量并生成 global/theme_quality.json
python backend/analytics/run_analytics.py --theme-quality-only

# 只生成 integrated.json
python backend/analytics/run_analytics.py --integrated-only --all
```

---

## 部署到 GitHub Pages

**可以部署。** 推送 `main` 分支后，GitHub Actions 会自动构建并发布静态站点。

访问地址：`https://<你的用户名>.github.io/CS3320/`

### 首次启用

1. 打开 GitHub 仓库 → **Settings** → **Pages**
2. **Build and deployment** → Source 选 **GitHub Actions**
3. 将代码 push 到 `main`（含 `.github/workflows/deploy-pages.yml`）
4. 在 **Actions** 页查看「Deploy to GitHub Pages」是否成功

### 关于数据体积

| 内容 | 大约体积 | 能否直接进 Git |
|------|----------|----------------|
| 前端构建产物 | ~2 MB | 可以（由 Actions 生成，不入库） |
| 全量 `public/data` | ~400 MB | **不建议**（超 GitHub 单文件/仓库推荐上限） |

因此默认 workflow **只部署前端**；若仓库里没有 `deploy/pages-data/`，网页能打开但选不了剧本。

### 带演示数据部署（推荐）

本地已有全量数据时，抽取一小部分提交到仓库：

```bash
python scripts/sync_frontend_data.py
python scripts/prepare_pages_data.py --max-plays 24
git add deploy/pages-data
git commit -m "Add demo data for GitHub Pages"
git push
```

之后每次 push 会自动把 `deploy/pages-data` 打进站点。可用 `--script-id` 指定具体剧本。

### 本地预览 GitHub Pages 路径

```bash
cd frontend
VITE_BASE_PATH=/CS3320/ npm run build
npx vite preview --base /CS3320/
```

### 全量数据上线

GitHub Pages 不适合托管 400MB+ JSON，可选方案：

- **Netlify / Vercel / 自建服务器**：构建时执行 `sync_frontend_data.py`，整包 `dist` 一起发布
- **对象存储 + CDN**：数据放 OSS/S3，前端改 `VITE_DATA_BASE` 外链加载（需自行扩展）
- **Release 附件**：大文件放 GitHub Release，CI 下载后再 build（需自行改 workflow）
