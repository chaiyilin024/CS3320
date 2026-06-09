# 数据契约（JSON Schema Draft-07）

```
schemas/
├── common/definitions.schema.json   # 行当、体裁、情节阶段等枚举
├── cleaned/                         # 预处理产出
└── analytics/                       # 分析产出
```

## 路径对照

| Schema | 输出 |
|--------|------|
| `catalog` | `artifacts/cleaned/catalog.json` |
| `play` | `artifacts/cleaned/plays/{id}.json` |
| `play_role` | `artifacts/analytics/plays/{id}/role.json` |
| `network` | `.../network.json` |
| `theme` | `.../themes.json` |
| `narrative` | `.../narrative.json` |
| `integrated` | `.../integrated.json` |
| `role_analysis` 等 | `artifacts/analytics/global/*.json` |

## 校验

```bash
pip install jsonschema
python -m jsonschema -i artifacts/cleaned/plays/01001012.json schemas/cleaned/play.schema.json
pytest tests/test_schemas.py
```
