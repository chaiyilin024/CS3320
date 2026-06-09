# 前端

Vue 3 + ECharts。静态读取 `public/data/`（本地由 `sync_frontend_data.py` 或 `copy_demo_to_public.py` 填充）。

## 路由

| 路径 | 任务 |
|------|------|
| `/` | 总览 |
| `/role` | 一 行当 |
| `/network` | 二 网络 |
| `/theme` | 三 主题 |
| `/narrative` | 四 叙事 |
| `/integrated` | 五 综合 |

## 数据

| 文件 | 用途 |
|------|------|
| `data/catalog.json` | 剧本列表 |
| `data/analytics/global/*.json` | 跨剧聚合 |
| `data/analytics/plays/{id}/*.json` | 单剧分析 |
| `data/plays/{id}.json` | 正文下钻（阶段子网络等） |

## 跨页联动（Pinia `FilterState`）

- `scriptId` — 当前剧本  
- `selectedCharacterIds` / `selectedTopicIds` — 高亮人物、主题  
- `narrativeBlockRange` — 叙事阶段或 brush 区间 → 网络页过滤子图  

## 命令

```bash
# 全库数据（本地开发）
python scripts/sync_frontend_data.py

# 演示数据（与 Pages 一致）
python scripts/copy_demo_to_public.py

cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # 产物 frontend/dist
```

默认剧本 `01001012`（黄鹤楼）。
