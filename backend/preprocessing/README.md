# 数据预处理模块说明

本文档面向 **数据预处理与清洗** 分工：说明原始数据从哪来、应产出哪些文件、各步骤用什么方法，以及如何为下游分析、前端提供稳定输入。

契约定义见 `schemas/cleaned/`；下游消费见 `backend/analytics/README.md`、`frontend/README.md`。

---

## 1. 你在流水线中的位置

```
原始数据                    预处理组（本文档）                 分析组 / 前端
────────                    ───────────────                 ────────────
zip + PDF + 数据说明.xlsx  →  artifacts/cleaned/      →     analytics/
                             catalog.json                    前端选剧
                             plays/{script_id}.json          正文下钻
```

**原则**：

- **只写** `artifacts/cleaned/`，格式符合 `schemas/cleaned/*.schema.json`。
- **不写** `artifacts/analytics/`；`characters[].hangdang_inferred` 预处理阶段保持 `null`（由分析组回填到 analytics 产物）。
- 尽量保证 **block_index 连续、speaker_id 可对齐、共现边完整**，分析组即可直接跑模型。

---

## 2. 读什么（输入）

### 2.1 原始数据（本地，通常不进 Git）

| 路径 | 说明 |
|------|------|
| `data/京剧剧本/*.zip` | 按集合打包的 PDF；文件名如 `01000000.zip` |
| `data/京剧剧本/数据说明.xlsx` | 集合名称、体量、备注（导出为 `configs/collections.yaml`） |
| `example/01001012_黄鹤楼.pdf` | **金样例**，优先打通整条流水线 |

zip 内 PDF 命名：`{script_id}_{剧名}.pdf`，例如 `01001012_黄鹤楼.pdf`。

### 2.2 配置文件（仓库内维护）

| 路径 | 用途 |
|------|------|
| `configs/collections.yaml` | `collection_id` → `collection_name`、来源丛书备注 |
| `configs/pipeline.yaml` | 数据根路径、解压缓存目录、批处理剧本列表、`parse_version` |

`collections.yaml` 可由 `数据说明.xlsx` 脚本导出，例如：

```yaml
"01000000":
  name: 戏考
  xlsx_code: "1000000"
"02000000":
  name: 国剧大成
  xlsx_code: "2000000"
```

### 2.3 参考文档（不要求程序读取）

| 路径 | 用途 |
|------|------|
| `doc/question.png` | 赛题五项任务，指导应抽取哪些字段 |
| `schemas/cleaned/*.schema.json` | 产出字段与类型的唯一标准 |

---

## 3. 产出什么（输出）

### 3.1 目录结构

```
artifacts/cleaned/
├── catalog.json                 ← catalog.schema.json
└── plays/
    ├── 01001012.json            ← play.schema.json
    └── ...
```

### 3.2 `catalog.json`（全库索引）

| 字段 | 谁用 | 说明 |
|------|------|------|
| `version`, `generated_at` | 全员 | 契约版本与生成时间 |
| `pipeline` | 助教复现 | `parse_version`, `play_count_total` 等 |
| `plays[]` | 前端、分析 | 每剧摘要一行，供列表筛选 |

每条 `plays[]` 至少包含：`script_id`, `title`, `collection_id`, `collection_name`, `source_pdf`。  
建议同时写入：`page_count`, `char_count`, `character_count`, `block_count`, `parse_quality`, `output_path`, `tags`（见下）。

### 3.3 `plays/{script_id}.json`（单剧结构化剧本）

| 区块 | Schema | 下游用途 |
|------|--------|----------|
| 元信息 | `play` 顶层 + `metadata` | 溯源、质量评估 |
| `characters[]` | `character.schema.json` | 任务一：行当、特征 |
| `scenes[]` | `scene.schema.json` | 任务四：场次（可选但推荐） |
| `blocks[]` | `block.schema.json` | 任务三/四：文本与时序 |
| `cooccurrence_edges_raw[]` | `cooccurrence_edge.schema.json` | 任务二：构图 |

### 3.4 建议写入的 `tags`（减轻分析组负担）

在 `catalog.plays[].tags` 与可选 `play.tags` 中提供：

| 键 | 方法 | 说明 |
|----|------|------|
| `genre_inferred` | 规则 / 关键词 | 历史剧、公案剧等，枚举见 `definitions.schema.json` |
| `era_inferred` | 规则 / 词典 | 如：三国、宋代、清代 |

分析组可直接用于 global 聚合；若缺失，分析组需自行推断。

### 3.5 提交与样例

- 全量 `artifacts/cleaned/` 体积大，本地保留；仓库提交 **`artifacts/samples/cleaned/`**（至少黄鹤楼 `01001012` + `catalog` 子集）。
- 联调前通知分析组：路径、`parse_version`、已知坏案列表。

### 3.6 校验

```bash
pip install jsonschema pdfplumber
python -m jsonschema -i artifacts/cleaned/catalog.json schemas/cleaned/catalog.schema.json
python -m jsonschema -i artifacts/cleaned/plays/01001012.json schemas/cleaned/play.schema.json
pytest tests/test_schemas.py
```

---

## 4. 处理流程与推荐方法

整体四步：**ingest → extract → clean → export**，由 `run_pipeline.py` 串联。

```
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ ingest  │ → │ extract │ → │  clean  │ → │ export  │
│ 解压索引 │   │ PDF→文本 │   │ 结构化  │   │ 写 JSON │
└─────────┘   └─────────┘   └─────────┘   └─────────┘
```

---

### 4.1 Ingest：解压与目录索引

**输入**：`data/京剧剧本/{collection_id}.zip`  
**输出**：内存/磁盘文件列表 + `collection_id` / `collection_name`

**方法**：

1. 遍历 zip，解压到缓存目录（如 `artifacts/cache/pdf/`），避免每次重解压。
2. 从 PDF 文件名解析：
   - `script_id`：文件名前缀 8 位数字（`01001012`）
   - `title`：下划线后剧名（去掉 `.pdf`）
3. `collection_id`：由所在 zip 文件名得到（如 `01000000.zip` → `01000000`）。
4. 注意 **zip 内中文文件名编码**：Windows 打包可能为 GBK，解压时使用 `zipfile` 并指定 `metadata_encoding='gbk'`（Python 3.11+）或手动解码，避免剧名乱码。
5. 维护「已处理 / 失败 / 跳过」清单，供 `catalog.pipeline` 统计。

**依赖**：标准库 `zipfile`、`pathlib`

---

### 4.2 Extract：PDF 文本抽取

**输入**：单份 PDF 二进制  
**输出**：按页或全文的原始字符串 + `page_count`

**方法（按优先级）**：

| 方案 | 库 | 适用 |
|------|-----|------|
| 首选 | `pdfplumber` 或 `pymupdf`（fitz） | 可复制文本的电子版剧本 |
| 兜底 | `paddleocr` / `tesseract` + `ocr_used: true` | 扫描版、乱码页 |

**实践建议**：

- 先抽全文，再按行切分；记录 `metadata.warnings`（某页空白、OCR 低置信等）。
- 计算 `parse_quality`（0–1）：例如「成功提取字符数 / 页数」「块类型识别成功率」的加权。
- 保留页码映射，写入 `blocks[].page_no`（可选）。

**依赖**：`pdfplumber` 或 `pymupdf`；可选 `paddleocr`

---

### 4.3 Clean：结构化与清洗

**输入**：原始文本  
**输出**：`characters`, `scenes`, `blocks`, `cooccurrence_edges_raw`

这是预处理的核心，建议分模块实现。

#### （1）文本规范化

- 统一繁简（可选 `opencc`）、全半角、空白行。
- 去掉页眉页脚、纯页码行（正则：`^\d+$`、`第\s*\d+\s*页`）。
- 合并因 PDF 换行导致的断句（行末非句号且下一行非角色名则拼接）。

#### （2）块切分 `blocks[]`

按京剧剧本常见版式识别块类型（`block.schema.json` 的 `type`）：

| 模式（示例） | type | 说明 |
|--------------|------|------|
| `刘备：（白）……` / `刘备：……` | `dialogue` | 对白；括号内「白/念」记入 `performance_tags` |
| `【西皮二六】`、`（唱）` | `aria` | 唱段 |
| `（周瑜上）`、`（同上场）` | `stage_direction` | 舞台说明 |
| `第一场`、`地点：城楼` | `scene_heading` | 场次标题 |
| 人物表、行当标注行 | `character_list` | 可单独成块或只解析进 `characters` |

为每个块分配：

- `block_id`：`b_{block_index}`
- `block_index`：从 0 递增，**全剧唯一且连续**
- `speaker_id` / `speaker_name_raw`：对白块必填其一；说明块为 `null`
- `performance_tags`：从「唱/念/做/打」等标记映射到枚举

#### （3）人物表 `characters[]`

| 字段 | 方法 |
|------|------|
| `character_id` | `c_` + 姓名规范化（去空格、统一别名指向主名） |
| `hangdang_labeled` | 剧本人物表中「生/旦/净/丑」等显式标注；无则 `null` |
| `hangdang_inferred` | **固定 `null`**（勿在预处理填） |
| `traits` | 从人物说明句抽取：性别、年龄、身份、性格词；表演倾向统计 |
| `description_raw` / `description_clean` | 介绍段原文 / 清洗后 |
| `line_count`, `first_appearance_block` | 遍历 `blocks` 统计 |
| `is_main` | 规则：台词量 Top-N 或超过全剧台词 5% |

**NER 可选**：`jieba` 词典 + 戏曲人名词典；以规则为主，模型为辅。

#### （4）场次 `scenes[]`

- 用 `scene_heading` 块切分场次，`scene_index` 从 1 递增。
- `block_range`：本场 `[首块 index, 末块 index]`。
- `character_ids`：本场 `blocks` 中出现过的 `speaker_id` 去重。

#### （5）共现边 `cooccurrence_edges_raw[]`

供分析组直接构图，避免重复实现：

| 边类型 | 统计方式 | `relation_types` |
|--------|----------|------------------|
| 对话 | 相邻或同一轮对白双方 | `对话` |
| 同场 | 同一 `scene_id` 内人物两两共现 | `同场` |
| 唱和 | 连续唱段涉及多角色（可选） | `唱和` |

- `weight`：共现次数或对话轮次。
- `dialogue_count` / `same_scene_count`：分项计数（可选）。
- 边为无向图时，约定 `source_id < target_id` 字典序，避免重复边。

#### （6）体裁 / 时代标签（可选）

- 标题、首幕说明、人物身份关键词 → `tags.genre_inferred`、`tags.era_inferred`。
- 简单关键词表即可，不必上大模型。

**依赖**：`jieba`、`regex` / `re`；可选 `opencc-python-reimplemented`

---

### 4.4 Export：写出 JSON 与 catalog

1. 写出 `plays/{script_id}.json`，UTF-8，`ensure_ascii=False`。
2. 汇总全部成功条目 → `catalog.json`。
3. 失败剧本写入 `artifacts/cleaned/failed.json`（本仓库 schema 外，便于排查）：

```json
{ "script_id": "01009999", "reason": "pdf_empty", "source_pdf": "..." }
```

---

## 5. 代码目录与运行方式

```
backend/preprocessing/
├── README.md              # 本文档
├── run_pipeline.py        # 入口
├── ingest/
│   ├── unzip.py           # 解压、GBK 文件名
│   └── index.py           # 扫描 pdf 列表
├── extract/
│   └── pdf_text.py        # pdfplumber / OCR
├── clean/
│   ├── normalize.py       # 文本清洗
│   ├── segment.py         # 切 blocks
│   ├── characters.py      # 人物表与 traits
│   ├── scenes.py          # 场次
│   └── edges.py           # 共现边
├── export/
│   └── write_json.py      # play + catalog
└── utils/
    ├── ids.py             # script_id、character_id 规范化
    └── quality.py         # parse_quality 计算
```

**运行示例**：

```bash
# 单剧金样例（联调）
python backend/preprocessing/run_pipeline.py --pdf example/01001012_黄鹤楼.pdf \
  --collection-id 01000000

# 指定 zip 内一批
python backend/preprocessing/run_pipeline.py --zip data/京剧剧本/01000000.zip

# 按 pipeline.yaml 剧本 ID 列表
python backend/preprocessing/run_pipeline.py --config configs/pipeline.yaml

# 仅重建 catalog（plays 已存在）
python backend/preprocessing/run_pipeline.py --catalog-only
```

---

## 6. 推荐技术栈

| 类别 | 库 | 用途 |
|------|-----|------|
| 基础 | `python 3.10+`, `pandas`（可选） | 批处理与统计 |
| PDF | `pdfplumber` 或 `pymupdf` | 文本抽取 |
| OCR | `paddleocr` / `pytesseract` | 扫描版兜底 |
| 中文 | `jieba`, `opencc`（可选） | 分词、繁简 |
| 校验 | `jsonschema` | 产出合规 |
| 配置 | `pyyaml` | `collections.yaml` / `pipeline.yaml` |

`requirements.txt` 建议单独列出 preprocessing 依赖，与分析组区分。

---

## 7. 与下游的字段契约（必达）

分析组 **强依赖** 以下字段，请优先保证质量：

| 字段 | 分析任务 | 最低要求 |
|------|----------|----------|
| `blocks[].block_index` | 三、四 | 连续从 0 开始 |
| `blocks[].text`, `type` | 三、四 | 非空、类型合理 |
| `blocks[].speaker_id` | 二、三、五 | 对白块尽量有，且 ID 在 `characters` 中存在 |
| `characters[].traits` | 一 | 至少有 gender/identity 之一或 `description_clean` |
| `characters[].hangdang_labeled` | 一 | 有则填，无则 null |
| `cooccurrence_edges_raw` | 二 | 每剧至少对话边或同场边 |
| `catalog.plays[].tags.genre_inferred` | 二 global | 推荐预填 |
| `hangdang_inferred` | — | **保持 null** |

---

## 8. 与兄弟组协作

| 事项 | 预处理 | 分析 | 前端 |
|------|--------|------|------|
| 黄鹤楼 `01001012` 先通 | ✅ 负责 | 等待 cleaned | 可用 samples mock |
| schema 变更 | 发起 PR | 同步改模型 | 同步改类型 |
| 解析率过低 | 修 extract/clean | 不硬啃 PDF | — |
| catalog 列表 | 维护 | 批处理入口 | 选剧下拉 |

**沟通清单**（每周末）：

1. 本周新增剧本数、`parse_quality` 均值  
2. `failed.json` Top 原因  
3. 是否变更 `parse_version`（变更需重跑分析）

---

## 9. 分期交付建议

| 阶段 | 目标 | 范围 |
|------|------|------|
| W12 | 金样例端到端 | `01001012` 黄鹤楼 → 合规 `play.json` + catalog 一条 |
| W13 | 单集合批量 | `01000000.zip`（戏考）抽样 50–100 剧 |
| W14 | 多集合 + 标签 | 2–3 个 zip；`genre_inferred` 规则 v1；共现边稳定 |
| 答辩前 | 复现脚本 + samples | `run_pipeline.py` + `artifacts/samples/cleaned/` |

---

## 10. 质量检查清单

处理每剧后自检：

- [ ] `script_id` 为 8 位数字，与文件名一致  
- [ ] `blocks` 非空，`block_index` 无跳号  
- [ ] 对白块 `speaker_id` 均能在 `characters` 中找到  
- [ ] `hangdang_inferred` 均为 `null`  
- [ ] `cooccurrence_edges_raw` 非空（主人物 ≥ 2 时）  
- [ ] `metadata.parse_quality` 已填；低分剧记入 `failed.json` 或 `warnings`  
- [ ] 通过 `play.schema.json` 校验  

---

## 11. 速查表

| 步骤 | 读 | 写 | 核心方法 |
|------|----|----|----------|
| Ingest | zip、xlsx→yaml | 缓存 pdf 列表 | zipfile（GBK 名）、文件名解析 |
| Extract | PDF | 原始文本、页数 | pdfplumber / OCR |
| Clean | 原始文本 | characters、scenes、blocks、edges | 正则 + 规则切分、jieba |
| Export | 内存结构 | `catalog.json`、`plays/*.json` | jsonschema 校验 |

**金样例路径**：`example/01001012_黄鹤楼.pdf`  
**下游文档**：`backend/analytics/README.md`、`frontend/README.md`  
**Schema 索引**：`schemas/README.md`
