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