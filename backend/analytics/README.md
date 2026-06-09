# 数据分析

**输入**：`artifacts/cleaned/`  
**输出**：`artifacts/analytics/plays/{id}/*.json`、`artifacts/analytics/global/*.json`

## 五任务与方法（当前实现）

| 任务 | 产出 | 方法 |
|------|------|------|
| 一 行当 | `role.json`、`role_analysis.json` | 规则映射 `traits`→行当；有标注用 `hangdang_labeled`，否则 `hangdang_inferred`+置信度；全局特征×行当共现矩阵；按集合/时代聚合 |
| 二 网络 | `network.json`、`network_compare.json` | 主人物为节点，`cooccurrence_edges_raw` 为边；自研图算法算度/介数/密度/聚类/模块度；按体裁/集合对比指标分布 |
| 三 主题 | `themes.json`、`theme_patterns.json` | 全库 `theme.json` 锚定种子 + 关键词打分（`global_keyword`）；单剧块级 argmax；跨剧按语义 label 对齐热力与组合模式 |
| 四 叙事 | `narrative.json`、`narrative_templates.json` | 滑动窗口（20 块）算对白/唱/动作/情感/张力五维曲线；张力变点切五阶段；全库聚类得叙事模板 |
| 五 综合 | `integrated.json` | 人物×主题关键词重合；各阶段子图密度；生成 `correlations` 与 `summary_insights` |

可选：`--theme-llm` 调用 OpenAI 兼容 API 生成主题（失败回退 keyword）。

## 命令

```bash
pip install -r backend/requirements.txt

# 全库
python backend/analytics/run_analytics.py --all

# 单剧
python backend/analytics/run_analytics.py --script-id 01001012

# 仅全局聚合
python backend/analytics/run_analytics.py --global-only

# 仅综合关联
python backend/analytics/run_analytics.py --integrated-only --all

# 重训全局主题模型
python backend/analytics/run_analytics.py --train-global-theme-only

# 仅重算 themes + global 主题聚合
python backend/analytics/run_analytics.py --themes-only --all

# 一键脚本
bash scripts/run_analytics.sh
```

## 产出结构

```
artifacts/analytics/
├── global/          # role_analysis, network_compare, theme_patterns, narrative_templates, theme_quality
└── plays/{id}/
    ├── role.json
    ├── network.json
    ├── themes.json
    ├── narrative.json
    └── integrated.json
```

契约：`schemas/analytics/` · 下游：[frontend/README.md](../../frontend/README.md)
