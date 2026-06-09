# 预处理

**输入**：`data/京剧剧本/*.zip`、PDF  
**输出**：`artifacts/cleaned/catalog.json`、`artifacts/cleaned/plays/{script_id}.json`

## 流水线

```
ingest（解压索引）→ extract（PDF 抽文本）→ clean（结构化）→ export（写 JSON）
```

| 步骤 | 方法 |
|------|------|
| Ingest | `zipfile` 解压（GBK 文件名）；从 `{script_id}_{剧名}.pdf` 解析 ID 与剧名 |
| Extract | `pdfplumber` 按页抽文本；计算 `parse_quality` |
| Clean | 正则切 `blocks`（对白/唱段/舞台说明等）；规则建 `characters`、`scenes`；统计 `cooccurrence_edges_raw`（对话、同场）；`jieba` + 关键词推断 `genre_inferred` / `era_inferred` |
| Export | 写出 play JSON，汇总 `catalog.json`；`jsonschema` 校验 |

**约定**：预处理不写 `hangdang_inferred`（保持 `null`）；`block_index` 从 0 连续编号。

## 命令

```bash
pip install -r backend/requirements.txt

# 按配置批处理（推荐）
python backend/preprocessing/run_pipeline.py --config configs/pipeline.yaml

# 单份 PDF（联调）
python backend/preprocessing/run_pipeline.py \
  --pdf example/01001012_黄鹤楼.pdf --collection-id 01000000

# zip 内抽样
python backend/preprocessing/run_pipeline.py \
  --zip data/京剧剧本/01000000.zip --limit 5

# 仅从已有 plays 重建 catalog
python backend/preprocessing/run_pipeline.py --catalog-only

# 一键脚本
bash scripts/run_preprocess.sh
```

## 目录

`ingest/` · `extract/pdf_text.py` · `clean/` · `export/write_json.py` · `run_pipeline.py`

配置：`configs/pipeline.yaml`、`configs/collections.yaml`  
契约：`schemas/cleaned/`
