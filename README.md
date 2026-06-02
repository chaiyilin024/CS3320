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