# 前端开发说明

本文档说明前端应消费哪些数据、五个赛题任务分别对应哪些页面与图表，以及多视图如何联动。类型定义以 `schemas/` 下的 JSON Schema 为准。

---

## 1. 前端读哪些数据？

### 1.1 主数据源：`artifacts/analytics/`（对应 `schemas/analytics/`）

前端**核心业务数据**全部来自分析产物，与 `schemas/analytics` 一一对应：

| 读取文件 | Schema | 用途 | 单剧 / 全局 |
|----------|--------|------|-------------|
| `global/role_analysis.json` | `role_analysis.schema.json` | 任务一：跨剧行当分布、特征→行当、未标注推断列表 | 全局 |
| `plays/{id}/role.json` | `play_role.schema.json` | 任务一：当前剧本人物行当与推断详情 | 单剧 |
| `plays/{id}/network.json` | `network.schema.json` | 任务二：人物关系力导向图 | 单剧 |
| `global/network_compare.json` | `network_compare.schema.json` | 任务二：按体裁/集合对比网络指标 | 全局 |
| `plays/{id}/themes.json` | `theme.schema.json` | 任务三：主题构成、关键词、代表片段 | 单剧 |
| `global/theme_patterns.json` | `theme_patterns.schema.json` | 任务三：剧本×主题热力、主题组合 | 全局 |
| `plays/{id}/narrative.json` | `narrative.schema.json` | 任务四：情节阶段、节奏曲线、唱念做打 | 单剧 |
| `global/narrative_templates.json` | `narrative_templates.schema.json` | 任务四：跨剧叙事模板/体裁平均节奏 | 全局 |
| `plays/{id}/integrated.json` | `integrated.schema.json` | 任务五：跨维度关联、洞察摘要、综合矩阵 | 单剧 |

**开发阶段**：可将上述 JSON 放在 `frontend/public/data/`，或通过 FastAPI 的 `/api/*` 获取（见第 6 节）。

### 1.2 辅助数据源：`artifacts/cleaned/`（对应 `schemas/cleaned/`）

`schemas/analytics` **不包含**剧本列表与正文，以下两项由预处理提供，前端**仅作导航与下钻**，不做复杂分析：

| 读取文件 | Schema | 前端用途 |
|----------|--------|----------|
| `catalog.json` | `catalog.schema.json` | 剧本下拉/搜索、集合筛选、KPI 卡片（人物数、块数等） |
| `plays/{id}.json` | `play.schema.json` | 可选：点击网络节点或主题证据时，展示 `blocks` 原文片段 |

若工期紧，**第一期可只接 `catalog.json`**，正文下钻第二期再接 `play.json`。

### 1.3 不必直接读的 Schema

| 路径 | 说明 |
|------|------|
| `schemas/common/definitions.schema.json` | 枚举与类型约定；建议据此生成 TS 类型，不必运行时读取 |
| `schemas/cleaned/character.schema.json` 等子 schema | 已内嵌在 `play.schema.json` 中，按 play 文件解析即可 |

---

## 2. 应用信息架构（页面）

```
App
├── 总览 Dashboard          ← catalog + 各 global 摘要
├── 任务一 人物与行当       ← role_analysis + play role
├── 任务二 人物关系网络     ← network + network_compare
├── 任务三 主题分析         ← themes + theme_patterns
├── 任务四 叙事结构         ← narrative + narrative_templates
└── 任务五 综合探索         ← integrated（并联动以上单剧数据）
```

路由示例：

- `/` — 总览  
- `/role` — 任务一  
- `/network` — 任务二  
- `/theme` — 任务三  
- `/narrative` — 任务四  
- `/integrated` — 任务五  

每个任务页顶部共用 **剧本选择器**（数据来自 `catalog.json`）。

---

## 3. 全局状态与联动

建议用 Pinia / Zustand 维护一份 `FilterState`，在各视图间共享：

```ts
interface FilterState {
  scriptId: string | null;           // 当前剧本，如 "01001012"
  collectionId: string | null;       // 集合筛选，如 "01000000"
  genre: string | null;              // 体裁：历史剧 / 家庭剧 / …
  selectedCharacterIds: string[];    // 高亮人物，如 ["c_刘备"]
  selectedTopicIds: number[];        // 高亮主题 topic_id
  narrativeBlockRange: [number, number] | null;  // brush 选中的 block_index 区间
}
```

**联动规则（最低实现）**：

| 用户操作 | 影响 |
|----------|------|
| 切换 `scriptId` | 所有单剧 JSON 重新请求；全局图可保持 |
| 任务二点击节点 | 写入 `selectedCharacterIds`；任务一表格高亮同行当人物 |
| 任务三点击主题 | 写入 `selectedTopicIds`；任务四节奏图标记对应 `dominant_topic_id` 区段 |
| 任务四 brush 选区 | 写入 `narrativeBlockRange`；任务二可过滤该区间内的边（若后端提供子图则更好，否则前端按 block 过滤） |
| 总览选集合/体裁 | 过滤 `catalog.plays`；全局对比图按 `genre` / `collection_id` 筛选 |

---

## 4. 五个任务：视图与字段对照

### 任务一：人物扮相与行当分析

**赛题目标**：由人物特征推断行当；比较特征与行当关系在不同时代/来源中的变化。

**读取数据**：

- 单剧：`plays/{scriptId}/role.json`
- 全局：`global/role_analysis.json`
- 列表：`catalog.json`（选剧、按 `collection_name` / `tags.genre_inferred` 筛选）

**推荐视图**：

| 视图 | 图表 | 主要字段 | 交互 |
|------|------|----------|------|
| 行当分布 | 饼图 / 环形图 | `hangdang_distribution` 或全局 `by_collection[].hangdang_distribution` | 点击扇区 → 过滤人物表 |
| 特征→行当 | 桑基图或热力图 | `global_feature_hangdang_matrix`：`feature`, `hangdang`, `count`, `ratio` | hover 显示 count/ratio |
| 人物明细表 | 表格 | `characters[]`：`name`, `hangdang_labeled`, `hangdang_inferred`, `hangdang_final`, `confidence`, `top_features` | 行点击 → `selectedCharacterIds` |
| 未标注推断 | 表格 + 进度条 | `inference_results[]`（全局）或单剧中 `hangdang_inferred` 非空且 labeled 为空 | 按 `confidence` 排序 |
| 集合/时代对比 | 分面堆叠条 / 小 multiples | `by_collection[]`, `by_era_bucket[]` | 下拉切换维度 |

**可选增强**：单剧人物雷达图，字段来自 cleaned `play.json` 的 `characters[].traits`（若已接入）。

---

### 任务二：人物关系网络

**赛题目标**：构建主要人物互动网络；比较不同体裁剧本的网络结构差异。

**读取数据**：

- 单剧：`plays/{scriptId}/network.json`
- 全局：`global/network_compare.json`
- 元信息：`network.json` 内 `genre`；或 `catalog.plays[].tags.genre_inferred`

**推荐视图**：

| 视图 | 图表 | 主要字段 | 交互 |
|------|------|----------|------|
| 关系网络 | 力导向图（G6 / ECharts Graph） | `nodes[]`：`id`, `name`, `hangdang`, `degree`, `betweenness`；`links[]`：`source`, `target`, `weight`, `types` | 节点大小∝`degree`；颜色∝`hangdang`；拖拽、缩放；点击节点联动 |
| 核心人物 | 横向条形图 | `nodes` 按 `betweenness` 或 `degree` 排序 | 点击跳转网络中心 |
| 体裁网络对比 | 箱线图 / 小提琴图 | `by_genre[].metrics.density` 等 `values[]`；或 `plays[].metrics` | 选择体裁高亮对应点 |
| 集合对比 | 同上 | `by_collection[]` | 与体裁 Tab 切换 |
| 网络 KPI | 数字卡片 | `metrics`：`node_count`, `edge_count`, `density`, `avg_clustering` | — |

**节点/边编码建议**：

- 节点 `id` 与任务一 `character_id` 一致（`c_` 前缀）
- 边 `weight` 映射线宽；`types` 映射颜色或虚线样式

---

### 任务三：主题分析

**赛题目标**：提取剧本核心主题；跨剧本比较主题构成与组合模式。

**读取数据**：

- 单剧：`plays/{scriptId}/themes.json`
- 全局：`global/theme_patterns.json`

**推荐视图**：

| 视图 | 图表 | 主要字段 | 交互 |
|------|------|----------|------|
| 主题构成 | 饼图 / 旭日图 | `topics[]`：`label`, `weight`；或 `topic_composition[]` 与 `topics` 顺序对齐 | 点击主题 → `selectedTopicIds` |
| 关键词 | 词云 | `topics[].keywords`，可选 `keyword_weights` | 与主题选择联动 |
| 跨剧主题热力 | 热力图 | `play_topic_matrix[]`：`script_id`, `title`, `weights[]`；列标签 `topic_labels[]` | 行点击切换 `scriptId` |
| 主题组合 | 弦图 / 邻接矩阵 | `topic_cooccurrence[]`：`topic_a`, `topic_b`, `count`；`common_patterns[]`：`labels`, `support` | 点击组合筛选剧本列表 |
| 证据片段 | 列表 / 卡片 | `representative_blocks[]`：`text_snippet`, `block_index`, `score` | 点击可跳转任务四对应位置 |

---

### 任务四：叙事结构分析

**赛题目标**：识别情节阶段与节奏起伏；比较不同剧本叙事结构。

**读取数据**：

- 单剧：`plays/{scriptId}/narrative.json`
- 全局：`global/narrative_templates.json`
- 可选正文：`plays/{scriptId}.json` 的 `blocks[]`（剧本条带）

**推荐视图**：

| 视图 | 图表 | 主要字段 | 交互 |
|------|------|----------|------|
| 情节阶段 | 时间轴 / Storyline | `plot_stages[]`：`stage`, `label`, `block_range` | 点击阶段 → 设置 `narrativeBlockRange` |
| 节奏曲线 | 多系列折线 / 面积图 | `rhythm_series[]`：`block_index`, `action_intensity`, `dialogue_density`, `aria_ratio`, `emotion_score` | brush 选 `block_index` 区间 |
| 唱念做打 | 堆叠条形图 | `performance_mark_distribution`；或 `performance_by_stage[]` | 与阶段轴对齐 |
| 块级条带 | 甘特/条形预览 | `block_annotations[]` 或 cleaned `blocks`：`block_index`, `type`, `speaker_id` | 与节奏图共享 x 轴 |
| 叙事模板对比 | 小 multiples 折线 | `by_genre[].avg_rhythm_curve`；`templates[]` | 选择模板高亮 example 剧本 |

**x 轴统一**：全页以 `block_index` 为叙事进度，便于与任务五、任务三联动的 `peak_block_index` 对齐。

---

### 任务五：综合探索（交互式可视分析系统）

**赛题目标**：综合人物、主题、叙事，探索维度间关联。

**读取数据**：

- 主文件：`plays/{scriptId}/integrated.json`
- 联动：同屏加载该剧本的 `role.json`、`network.json`、`themes.json`、`narrative.json`（或精简组件复用任务一至四）

**推荐视图**：

| 视图 | 图表 | 主要字段 | 交互 |
|------|------|----------|------|
| 洞察摘要 | 卡片列表 | `summary_insights[]` | 只读展示 |
| 人物×主题 | 热力图 | `character_topic_matrix[]`：`character_id`, `topic_id`, `strength` | 点击单元格 → 同时设置 character + topic |
| 阶段×网络 | 折线 + 迷你网络 | `stage_network_snapshots[]`：`stage`, `edge_density`, `block_range` | 选阶段刷新侧栏网络（可用全剧 network 加视觉淡化） |
| 关联明细 | 表格 / 图例 | `correlations[]`：按 `type` 分：`character_theme`, `network_stage`, `hangdang_narrative`, `theme_narrative` 等 | 筛选 type |
| 多视图仪表盘 | 2×2 布局 | 嵌入任务一至四的**缩小版**组件，共用 `FilterState` | 任一子图操作更新全局状态 |

**任务五最低交付**：左侧洞察 + 人物×主题热力 + 一个可联动的网络/节奏缩略图即可答辩；完整 2×2 为加分项。

---

## 5. 总览页 Dashboard

不单独对应赛题，但答辩需要入口叙事。

| 组件 | 数据 | 说明 |
|------|------|------|
| 剧本选择 | `catalog.plays` | 搜索 `title`、`script_id`；树形按 `collection_name` |
| 库统计 | `catalog` + 各 `global/*` | 剧本数、人物数均值、主题数等 |
| 五任务入口 | 路由 | 带当前 `scriptId` query |
| 迷你预览 | 可选各 global 一张小图 | 如行当堆叠条、主题热力缩略 |

---

## 6. API 约定（若走后端）

与静态 JSON 字段一致，便于从 mock 切到 API：

| 方法 | 路径 | 对应文件 |
|------|------|----------|
| GET | `/api/catalog` | `catalog.json` |
| GET | `/api/plays/{script_id}/role` | `role.json` |
| GET | `/api/plays/{script_id}/network` | `network.json` |
| GET | `/api/plays/{script_id}/themes` | `themes.json` |
| GET | `/api/plays/{script_id}/narrative` | `narrative.json` |
| GET | `/api/plays/{script_id}/integrated` | `integrated.json` |
| GET | `/api/global/role` | `role_analysis.json` |
| GET | `/api/global/network` | `network_compare.json` |
| GET | `/api/global/themes` | `theme_patterns.json` |
| GET | `/api/global/narrative` | `narrative_templates.json` |

查询参数建议统一：`collection_id`, `genre`, `script_ids[]`。

---

## 7. 技术栈与目录建议

```
frontend/
├── README.md                 # 本文档
├── public/
│   └── data/                 # mock：与 artifacts 结构相同
│       ├── catalog.json      # 来自 cleaned（可复制一份）
│       └── analytics/
│           ├── global/
│           └── plays/01001012/
├── src/
│   ├── api/                  # fetch 封装
│   ├── stores/filter.ts      # FilterState
│   ├── types/                # 由 schema 生成的 TS 类型（可选）
│   └── views/
│       ├── Dashboard.vue
│       ├── RoleView.vue        # 任务一
│       ├── NetworkView.vue     # 任务二
│       ├── ThemeView.vue       # 任务三
│       ├── NarrativeView.vue   # 任务四
│       └── IntegratedView.vue  # 任务五
```

图表库（课程建议）：**ECharts**（统计图）+ **AntV G6**（网络图），UI 可用 Element Plus / Ant Design Vue。

---

## 8. 分期交付建议

| 阶段 | 目标 | 数据 |
|------|------|------|
| W12 | 静态 mock + 五页骨架 + 选剧 | `public/data` 仅黄鹤楼 `01001012` |
| W13 | 任务二网络 + 任务一行当 | 同上 + 全局 mock 各 1 个文件 |
| W14 | 任务三、四 + brush 联动 | 10–20 剧 `catalog` + 对应 analytics |
| 整合 | 接 API 或复制 `artifacts` | 与后端路径一致 |

---

## 9. 类型与 Schema 对照速查

在 `schemas/analytics/` 中打开对应文件即可查看完整字段与枚举；共享枚举（行当、体裁、情节阶段等）见 `schemas/common/definitions.schema.json`。

| 任务 | 必接 Schema 文件 |
|------|------------------|
| 一 | `play_role.schema.json`, `role_analysis.schema.json` |
| 二 | `network.schema.json`, `network_compare.schema.json` |
| 三 | `theme.schema.json`, `theme_patterns.schema.json` |
| 四 | `narrative.schema.json`, `narrative_templates.schema.json` |
| 五 | `integrated.schema.json`（+ 任务一至四单剧数据联动） |
| 导航 | `catalog`（cleaned，非 analytics 目录） |

---

## 10. 参考样例剧本

联调金样例：**`01001012` 黄鹤楼**（`example/01001012_黄鹤楼.pdf`）。  
请分析组优先产出该 `script_id` 的全套 `plays/01001012/*.json`，前端据此做 mock 与录屏案例。
