# CS3320

## 项目架构
```bash
始剧本/元数据 → 清洗标注 → NLP/网络/时序分析 → 分析结果 JSON/CSV
                              ↓
                        Flask/FastAPI
                              ↓
                            前端多视图
```
---
### 代码
```
CS3320/
├── README.md
├── doc/                          # 赛题/课程文档（已有）
├── data/                         # 原始 zip（gitignore，本地放）
├── example/                      # 样例 pdf（已有）
│
├── schemas/                      # ★ 接口契约（见 schemas/README.md）
│   ├── common/definitions.schema.json
│   ├── cleaned/                  # 预处理 → 分析
│   └── analytics/                # 分析 → 前端
│
├── configs/
│   ├── collections.yaml          # xlsx 导出的集合映射
│   └── pipeline.yaml             # 路径、批处理、抽样剧本列表
│
├── backend/                      # 数据分析 + API（可两人协作）
│   ├── preprocessing/            # 【分工1】预处理（见 backend/preprocessing/README.md）
│   │   ├── run_pipeline.py       # CLI 入口
│   │   └── ingest/ extract/ clean/ export/
│   │
│   ├── analytics/                # 【分工2】分析模型（见 backend/analytics/README.md）
│   │   ├── README.md             # 读什么、产出什么、方法说明
│   │   ├── role/ network/ theme/ narrative/ integrated/
│   │   └── run_analytics.py
│   │
│   ├── api/                      # FastAPI 读 analytics 产物
│   │   ├── main.py
│   │   └── routes/
│   └── requirements.txt
│
├── artifacts/                    # 生成物（gitignore 大文件，保留样例）
│   ├── cleaned/                  # 预处理输出
│   │   ├── catalog.json          # 全库索引
│   │   └── plays/{script_id}.json
│   ├── analytics/                # 分析输出
│   │   ├── global/               # 跨剧本聚合
│   │   └── plays/{script_id}/
│   └── samples/                  # 小样本（可提交仓库供老师复现）
│
├── frontend/                     # 【分工3】交互界面（见 frontend/README.md）
│   ├── README.md                 # 数据对接、五任务视图、联动说明
│   ├── src/views/                # Dashboard + 任务一至五
│   └── package.json
│
├── scripts/                      # 一键：预处理 → 分析 → 复制到 frontend/public
│   └── build_all.sh
└── tests/
    ├── test_schemas.py           # 校验 JSON 是否符合 schema
    └── fixtures/                 # 用 01001012 黄鹤楼 做金样例
```