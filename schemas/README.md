# Schemas 接口契约

JSON Schema **Draft-07**，供预处理、分析、前端三组对齐数据格式。

## 目录

```
schemas/
├── common/
│   └── definitions.schema.json   # 共享枚举与基础类型
├── cleaned/                      # 预处理 → 分析
│   ├── catalog.schema.json
│   ├── play.schema.json
│   ├── character.schema.json
│   ├── block.schema.json
│   ├── scene.schema.json
│   └── cooccurrence_edge.schema.json
└── analytics/                  # 分析 → 前端
    ├── role_analysis.schema.json      # 全局
    ├── play_role.schema.json          # 单剧
    ├── network.schema.json
    ├── network_compare.schema.json    # 全局
    ├── theme.schema.json
    ├── theme_patterns.schema.json     # 全局
    ├── narrative.schema.json
    ├── narrative_templates.schema.json # 全局
    └── integrated.schema.json
```

## 产物路径对照

| Schema | 输出路径 |
|--------|----------|
| `catalog` | `artifacts/cleaned/catalog.json` |
| `play` | `artifacts/cleaned/plays/{script_id}.json` |
| `role_analysis` | `artifacts/analytics/global/role_analysis.json` |
| `play_role` | `artifacts/analytics/plays/{script_id}/role.json` |
| `network` | `artifacts/analytics/plays/{script_id}/network.json` |
| `network_compare` | `artifacts/analytics/global/network_compare.json` |
| `theme` | `artifacts/analytics/plays/{script_id}/themes.json` |
| `theme_patterns` | `artifacts/analytics/global/theme_patterns.json` |
| `narrative` | `artifacts/analytics/plays/{script_id}/narrative.json` |
| `narrative_templates` | `artifacts/analytics/global/narrative_templates.json` |
| `integrated` | `artifacts/analytics/plays/{script_id}/integrated.json` |

## 版本约定

- 所有顶层 `catalog` / `global/*` 文件包含 `version`（如 `1.0`）与 `generated_at`。
- 破坏性变更时递增主版本，三组同步升级。

## 校验示例

```bash
pip install jsonschema
python -m jsonschema -i artifacts/cleaned/plays/01001012.json schemas/cleaned/play.schema.json
```

或使用 `tests/test_schemas.py`（待添加）。
