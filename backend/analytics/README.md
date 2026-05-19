# 数据分析模块说明

本文档面向 **数据分析 / 模型搭建** 分工：说明输入从哪来、应产出哪些文件、五个赛题任务各用什么方法，以及如何与预处理、前端对接。

契约定义见 `schemas/analytics/`；前端消费方式见 `frontend/README.md`。

---

## 1. 你在流水线中的位置

```
预处理组                    数据分析组（本文档）              前端组
─────────                  ─────────────────              ──────
PDF → cleaned/      →      analytics/            →      可视化 + 交互
     catalog.json            global/*.json
     plays/{id}.json         plays/{id}/*.json
```

**原则**：

- 只读 `artifacts/cleaned/`，**不直接解析 PDF**（解析问题找预处理组）。
- 只写 `artifacts/analytics/`，字段必须符合 `schemas/analytics/*.schema.json`。
- 体裁 `genre`、时代 `era` 等标签可来自 `catalog.plays[].tags` 或本组规则/NLP 推断，写入 analytics 产物供前端筛选。

---

## 2. 读什么（输入）

### 2.1 必读

| 路径 | Schema | 用途 |
|------|--------|------|
| `artifacts/cleaned/catalog.json` | `catalog.schema.json` | 剧本列表、`collection_id`、可选 `tags.genre_inferred` / `tags.era_inferred` |
| `artifacts/cleaned/plays/{script_id}.json` | `play.schema.json` | **单剧分析主输入** |

### 2.2 从 `play.json` 中重点使用的字段

| 字段 | 用于任务 |
|------|----------|
| `script_id`, `title`, `collection_id`, `collection_name` | 全任务元信息 |
| `characters[]` | 任务一（行当）、任务二（节点属性） |
| `characters[].traits` | 任务一特征向量 |
| `characters[].hangdang_labeled` | 任务一监督/评估 |
| `blocks[]` | 任务三（语料）、任务四（时序） |
| `blocks[].block_index`, `type`, `speaker_id`, `text`, `performance_tags` | 主题、节奏、唱念做打 |
| `scenes[]`, `scenes[].block_range` | 任务四阶段切分辅助 |
| `cooccurrence_edges_raw[]` | 任务二构图（优先使用，避免重复算） |

### 2.3 可选配置

| 路径 | 用途 |
|------|------|
| `configs/pipeline.yaml` | 批处理剧本列表、输入输出路径 |
| `configs/collections.yaml` | 集合码 → 名称，聚合 `by_collection` 时使用 |

### 2.4 不必读

- 原始 `data/京剧剧本/*.zip`、PDF（除非预处理未就绪、临时自救）
- `schemas/` 运行时不必解析；开发时对照即可

---

## 3. 产出什么（输出）

所有输出写入 `artifacts/analytics/`，与 schema **一一对应**：

### 3.1 单剧（每个 `script_id` 一个目录）

```
artifacts/analytics/plays/{script_id}/
├── role.json          ← play_role.schema.json
├── network.json       ← network.schema.json
├── themes.json        ← theme.schema.json
├── narrative.json     ← narrative.schema.json
└── integrated.json    ← integrated.schema.json
```

### 3.2 全局（跨剧本聚合，跑完批量后生成）

```
artifacts/analytics/global/
├── role_analysis.json         ← role_analysis.schema.json
├── network_compare.json       ← network_compare.schema.json
├── theme_patterns.json        ← theme_patterns.schema.json
└── narrative_templates.json   ← narrative_templates.schema.json
```

### 3.3 顶层元字段

每个 **global** 文件必须包含：

```json
{
  "version": "1.0",
  "generated_at": "2026-05-18T12:00:00+08:00",
  ...
}
```

单剧文件至少包含 `script_id`（`themes.json` 等 schema 已规定必填项）。

### 3.4 提交与联调

- 全库过大时：完整结果放本地 `artifacts/`，向仓库提交 **`artifacts/samples/`** 金样例（推荐 `01001012` 黄鹤楼全套 + 少量 global）。
- 前端 mock：复制到 `frontend/public/data/analytics/`（路径与上一致）。

### 3.5 校验

```bash
pip install jsonschema
python -m jsonschema \
  -i artifacts/analytics/plays/01001012/role.json \
  schemas/analytics/play_role.schema.json
# 对其余 8 个 schema 重复
pytest tests/test_schemas.py
```

---

## 4. 五个赛题任务：方法、输入、产出

### 任务一：人物扮相与行当分析

**赛题**：由性别、年龄、身份、性格、唱念做打等推断行当；比较特征—行当关系在不同来源/时代的变化。

| 项目 | 说明 |
|------|------|
| **输入** | `characters[]`（`traits`, `hangdang_labeled`） |
| **产出** | `plays/{id}/role.json`，`global/role_analysis.json` |
| **目录** | `backend/analytics/role/` |

**推荐方法**（由易到难，可组合）：

1. **规则映射（必做 baseline）**  
   - 根据 `traits.gender/identity/age` + `performance_cues` 映射到 `hangdang` / `hangdang_coarse`（如「妇人+青衣关键词→青衣」）。  
   - 已有 `hangdang_labeled` 的作为 `hangdang_final`，仅对缺失者输出 `hangdang_inferred` + `confidence`。

2. **监督分类（有标注时）**  
   - 特征：traits  one-hot + 文本统计（台词量、唱段占比）。  
   - 模型：`sklearn` 的 `LogisticRegression` / `RandomForest`；交叉验证汇报准确率。  
   - 输出：`inference_results[]`（`top_features` 可用 SHAP 或权重 Top-K 简化）。

3. **特征—行当关联（全局）**  
   - 统计 `feature=value` 与 `hangdang` 共现，算 `count`、`ratio`。  
   - 可选 **PMI** 写入 `trait_hangdang_links` / `global_feature_hangdang_matrix`。

4. **分集合 / 分时代**  
   - 按 `catalog` 的 `collection_id`、`tags.era_inferred` 分组重算 `hangdang_distribution`。

**依赖**：`pandas`, `scikit-learn`, `jieba`（若用文本特征）

---

### 任务二：人物关系网络

**赛题**：构建主要人物互动网络；比较不同体裁剧本的网络结构。

| 项目 | 说明 |
|------|------|
| **输入** | `cooccurrence_edges_raw[]`；可补充从 `blocks` 统计对话边 |
| **产出** | `plays/{id}/network.json`，`global/network_compare.json` |
| **目录** | `backend/analytics/network/` |

**推荐方法**：

1. **构图**  
   - 节点：`characters` 中 `is_main==true` 或度阈值以上；节点属性带 `hangdang`。  
   - 边：优先 `cooccurrence_edges_raw`；`weight` 可用对话次数 + 同场加权。  
   - `types`：保留预处理给的 `relation_types`，或规则标注「对话/同场」。

2. **网络指标**（`networkx`）  
   - `degree`, `betweenness`, `density`, `avg_clustering`  
   - 可选：`modularity`（社区发现 `louvain` / `greedy_modularity`）

3. **体裁对比**  
   - 从 `catalog.tags.genre_inferred` 或本组分类器得到 `genre`，写入 `network.json`。  
   - 全局：`by_genre[]`、`plays[]` 汇总各剧 `metrics`，箱线图用 `values[]`。

**依赖**：`networkx`，可选 `python-louvain`

---

### 任务三：主题分析

**赛题**：提取核心主题；跨剧本比较主题构成与组合模式。

| 项目 | 说明 |
|------|------|
| **输入** | `blocks[].text`（可过滤 `stage_direction` 降权） |
| **产出** | `plays/{id}/themes.json`，`global/theme_patterns.json` |
| **目录** | `backend/analytics/theme/` |

**推荐方法**：

1. **文本预处理**  
   - `jieba` 分词；停用词表；保留戏曲相关词。

2. **主题模型（二选一）**  
   - **LDA**（`gensim`）：全库训练 K 个主题（如 K=8~15），单剧文档主题分布 → `topic_composition`。  
   - **TF-IDF + NMF**（`sklearn`）：实现简单、效果稳定。  
   - 每个 `topic_id` 取 Top 词为 `keywords`，人工或模板赋 `label`（忠义、谋略、爱情…）。

3. **单剧输出**  
   - `topics[].weight`：该主题在本剧占比。  
   - `representative_blocks`：主题后验最高的若干 `block_id` + `text_snippet`。

4. **全局模式**  
   - `play_topic_matrix`：每剧一行 `weights[]`。  
   - `topic_cooccurrence`：同一剧中 weight > 阈值的 theme 两两共现。  
   - `common_patterns`：频繁项集（`mlxtend`）或简单共现 Top-N。

**依赖**：`jieba`, `gensim` 或 `sklearn`, `pandas`

---

### 任务四：叙事结构分析

**赛题**：根据表演标记与内容识别情节阶段、节奏起伏；跨剧本比较叙事结构。

| 项目 | 说明 |
|------|------|
| **输入** | `blocks[]`（`block_index`, `type`, `performance_tags`）；`scenes[]` |
| **产出** | `plays/{id}/narrative.json`，`global/narrative_templates.json` |
| **目录** | `backend/analytics/narrative/` |

**推荐方法**：

1. **唱念做打统计**  
   - 全剧 `performance_mark_distribution`；按 `plot_stages` 分段的 `performance_by_stage`。

2. **节奏时间序列 `rhythm_series`**（滑动窗口，窗口宽如 20 blocks）  
   - `dialogue_density`：窗口内 `type==dialogue` 占比。  
   - `aria_ratio`：`aria` 或 `performance_tags` 含「唱」占比。  
   - `action_intensity`：`action`/`combat` 或「做/打」占比。  
   - `emotion_score`：对窗口内文本做情感分析（`snownlp` / `transformers` 轻量模型）或词典法。

3. **情节阶段 `plot_stages`**  
   - **规则法**：按 `emotion_score` / `action_intensity` 峰谷切分为铺垫/发展/冲突/高潮/结局（changepoint 可用 `ruptures` 或简单分位数）。  
   - **辅助**：`scenes[].block_range` 合并为更大段。  
   - 每段生成简短 `label`（关键词或模板）。

4. **全局叙事模板**  
   - 对节奏曲线重采样到固定长度，按 `genre` 平均 → `by_genre[].avg_rhythm_curve`。  
   - 聚类（K-Means）得 `templates[]`（「起承转合型」等）。

**依赖**：`numpy`, `pandas`；可选 `snownlp`, `ruptures`

---

### 任务五：综合关联分析

**赛题**：综合人物、主题、叙事，探索维度间关联，支撑交互探索。

| 项目 | 说明 |
|------|------|
| **输入** | 本剧 `role.json`、`network.json`、`themes.json`、`narrative.json` 及 cleaned `play.json`（或在内存中保留中间结果） |
| **产出** | `plays/{id}/integrated.json` |
| **目录** | `backend/analytics/integrated/` |

**推荐方法**（无需新重型模型，以 **关联与汇总** 为主）：

1. **`character_topic_matrix`**  
   - 按 `speaker_id` 聚合其台词块，映射到 LDA 主题分布，得到人物—主题强度。

2. **`stage_network_snapshots`**  
   - 对每个 `plot_stages`，取 `block_range` 内子图，算 `edge_density`、`node_count`。

3. **`correlations[]`**  
   - `character_theme`：人物主题强度 Top 对。  
   - `network_stage`：相邻阶段 `edge_density` 差 → `edge_density_delta`。  
   - `hangdang_narrative`：某行当台词块的 `emotion_score` 峰值 `peak_block_index`。  
   - `theme_narrative`：主题权重高的阶段与 `plot_stages` 对齐。

4. **`summary_insights[]`**  
   - 模板生成 3~5 条中文结论（例：「冲突段网络密度上升 25%，主题『谋略』占比最高」）。

**依赖**：同任务一至四；`integrated` 应在单剧四模块之后运行。

---

## 5. 代码目录与运行方式（已实现）

当前仓库已包含可运行实现；未安装 `scikit-learn` / `jieba` 时自动降级为 **keyword 主题模型** 与内置图算法（不依赖 networkx）。

```
backend/analytics/
├── README.md                 # 本文档
├── run_analytics.py          # 入口：单剧 / 批量 / 仅 global
├── role/
│   ├── infer.py
│   └── aggregate.py
├── network/
│   ├── build_graph.py
│   └── compare.py
├── theme/
│   ├── train_lda.py
│   └── export_play.py
├── narrative/
│   ├── rhythm.py
│   └── stages.py
├── integrated/
│   └── correlate.py
└── utils/
    ├── io.py                 # 读写 JSON、校验 schema
    └── catalog.py            # 加载 catalog、迭代 script_id
```

**建议入口逻辑**：

```bash
# 单剧（联调）
python backend/analytics/run_analytics.py --script-id 01001012

# 批量（configs/pipeline.yaml 中的列表）
python backend/analytics/run_analytics.py --all

# 仅重算全局聚合（已有 plays/*）
python backend/analytics/run_analytics.py --global-only
```

---

## 6. 推荐技术栈

| 类别 | 库 | 用途 |
|------|-----|------|
| 基础 | `python 3.10+`, `pandas`, `numpy` | 表结构与聚合 |
| NLP | `jieba` | 分词 |
| 主题 | `gensim`（LDA）或 `sklearn`（NMF） | 任务三 |
| 分类 | `scikit-learn` | 任务一行当推断 |
| 网络 | `networkx` | 任务二 |
| 情感/节奏 | `snownlp` 或词典 | 任务四（可选） |
| 校验 | `jsonschema` | 产出合规 |
| 服务 | `fastapi`（`backend/api/`） | 只读转发 analytics JSON |

`requirements.txt` 建议与分析组合并，版本 pin 住以便助教复现。

---

## 7. 与预处理、前端的协作

| 事项 | 负责方 | 说明 |
|------|--------|------|
| `cooccurrence_edges_raw` 缺失 | 预处理 | 网络组可临时从 `blocks` 算，但应推动预处理补齐 |
| `tags.genre_inferred` | 预处理或分析 | 至少一方写入 `catalog`，网络/主题/global 依赖 |
| `hangdang_labeled` 大量为空 | 分析 | 强化规则/分类，并在文档中说明推断比例 |
| 接口变更 | 全员 | 改 `schemas/analytics` 后同步前端 README |
| 金样例 | 分析 | 优先交付 `01001012` 全套 + 4 个 global |

---

## 8. 分期交付建议

| 阶段 | 交付物 | 方法重点 |
|------|--------|----------|
| W12 | `01001012` 五类单剧 JSON + mock global | 规则行当、networkx 构图、TF-IDF 主题、规则节奏 |
| W13 | 50 剧 batch + `role_analysis` + `network_compare` | LDA 全库训练；分类器 v1 |
| W14 | `theme_patterns` + `narrative_templates` + `integrated` | 聚类模板、关联规则、insights |
| 答辩前 | `run_analytics.py` 一键复现 + `artifacts/samples/` | schema 全过校验 |

---

## 9. 质量与答辩注意

1. **可复现**：固定 `random_seed`；`themes.json` 的 `model.method` / `num_topics_global` 写清楚。  
2. **可解释**：推断行当给出 `top_features`；主题给出 `representative_blocks`。  
3. **与可视化一致**：枚举值使用 `schemas/common/definitions.schema.json`（行当、体裁、情节阶段）。  
4. **勿篡改 cleaned**：分析结果写新文件，回写 `hangdang_inferred` 仅出现在 analytics 产物中。  
5. **性能**：全库 LDA 可离线训练一次，增量剧只推理；全局聚合与单剧分析解耦（`--global-only`）。

---

## 10. 速查表

| 赛题任务 | 读 | 写 | 核心方法 |
|----------|----|----|----------|
| 一 行当 | `characters`, `catalog` | `role.json`, `role_analysis.json` | 规则 + sklearn 分类 + PMI |
| 二 网络 | `cooccurrence_edges_raw`, `characters` | `network.json`, `network_compare.json` | networkx 指标 + 分体裁聚合 |
| 三 主题 | `blocks.text` | `themes.json`, `theme_patterns.json` | jieba + LDA/NMF |
| 四 叙事 | `blocks`, `scenes` | `narrative.json`, `narrative_templates.json` | 滑动窗口 + 阶段切分 + 聚类 |
| 五 综合 | 一至四输出 + `play.json` | `integrated.json` | 跨表关联 + 模板洞察 |

Schema 路径对照：`schemas/README.md`  
前端字段与图表：`frontend/README.md`
