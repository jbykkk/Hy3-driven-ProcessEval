# 最终答案验证设计

最终答案验证位于 solver 之后，不参与模型请求，也不修改原始 inference 记录：

```text
benchmark reference_answer ----+
                               v
solver_outputs.jsonl --> 当前版本答案解析 --> 数学等价验证
                               |
                               v
              outputs/answer_verification.jsonl
```

验证记录以 `inference_id` 为单位，因此同一道题的多次独立调用会分别评分。当前同时保存：

- `exact_match`：去除外围数学定界符后的字符串是否完全相同。
- `math_equivalent`：使用 Hugging Face `math-verify` 解析为 SymPy 表达式后是否数学等价。
- `format_mismatch_but_equivalent`：字符串不同、但数学上等价，是本阶段重点审计的样本。
- `manual_review_recommended`：多答案、集合、矩阵、无法解析等需要更谨慎处理的情况。
- 参考答案、预测答案、解析出的规范表达式、验证器版本和错误信息。

例如 `\frac{4}{5}` 与 `0.8`、`5+6\sqrt{2}` 与 `6\sqrt{2}+5` 应判为数学等价，而不是因为字符串不同被误判。

运行全部已有结果：

```bash
uv run python -m evaluation.runner
```

只验证指定样本：

```bash
uv run python -m evaluation.runner --id math-test-prealgebra-0023
```

当前版本适合单个数值或代数表达式。包含多个根、无序集合、区间、坐标、单位或选择题标签的答案即使工具给出结果，也应按 `manual_review_recommended` 复核；后续再按答案类型增加专门规则。

## 当前 benchmark 的答案形态审计

GSM8K 的 100 题与 AIME 的 50 题在当前 benchmark 中都是整数参考答案。MATH 的 250 题更复杂，按参考答案字符串做启发式、互斥分类后得到：

| 答案形态 | 数量 |
| --- | ---: |
| 整数 | 167 |
| 分数或有理式 | 37 |
| 根式 | 12 |
| 元组、区间或多个答案 | 14 |
| 其他符号表达式 | 6 |
| 文本、选项或单位 | 3 |
| 角度 | 3 |
| 含 \(\pi\) 表达式 | 3 |
| 矩阵 | 3 |
| 复数 | 1 |
| 集合或多个根 | 1 |

这项分类用于规划验证器覆盖面，不替代数学语义判断。当前优先可靠覆盖整数、分数、根式及普通单表达式；结构化答案是下一阶段的主要人工复核候选。

## 首轮跨数据集实验

首轮共验证 6 次 inference，其中包含已有的 GSM8K 调用，以及 5 次新增调用：同一道 MATH 分数题重复两次、MATH 根式题一次、MATH 混合数题一次、AIME 2024 题一次。6 次最终答案均通过数学验证。

其中产生了两个真实的 `format_mismatch_but_equivalent=true` 样本：

- 根式预测为 `5 + 6\sqrt{2}`，参考答案为 `5+6\sqrt{2}`。
- 混合数预测为 `8\frac{4}{7}`，参考答案为紧凑写法 `8\frac47`；两者均被解析为 `60/7`。

分数题两次均输出 `\frac{4}{5}`，AIME 输出 `204`。这些结果说明验证层能够区分“字符串不同”和“数学答案不同”，但尚不代表结构化答案类型已获得充分覆盖。

## 第二轮 GSM8K/MATH 多格式实验

第二轮选择 2 道 GSM8K 与 4 道 MATH，覆盖货币和千位分隔符、等价单位、分数与小数、含 \(\pi\) 表达式、区间以及无序多根。6 道目标题最后均得到正确答案：

| 类型 | 模型预测 | 参考答案 | 结果 |
| --- | --- | --- | --- |
| 货币/千位分隔 | `1596`（从 `\$1,596` 提取） | `1596` | 正确 |
| 距离/等价单位 | `180000`（优先提取 `180,000 meters`，而非后述 `180 km`） | `180000` | 正确 |
| 分数/小数 | `0.5` | `\frac{1}{2}` | 数学等价 |
| 含 \(\pi\) 表达式 | `\frac{\pi}{3}` | `\frac{\pi}{3}` | 正确 |
| 区间 | `(-\infty,\,-3)` | `(-\infty, -3)` | 数学等价，保留人工复核标记 |
| 无序多根 | `-1, -\frac{3}{2}, 7` | `-\frac{3}{2}, -1, 7` | 集合等价，保留人工复核标记 |

实验促使答案 parser 升级到 `solution-parser-v1.2`：支持无显式 `Answer:` 标签的结论句、优先读取主要单位答案，以及从 `\(...\)` 数学片段中读取末尾等价表达。旧 inference 直接从原始回答重新解析，无需重复 API 调用。

多根题首次使用 high reasoning 时，4096 个 completion tokens 全部用于推理，`finish_reason=length` 且没有可见答案；以 low reasoning 重试后使用 1988 tokens 正常完成并验证正确。截断记录仍作为 `unverified` 历史证据保留，说明后续批量运行需要监控 `finish_reason` 和 reasoning token 占比。

评测入口现在执行生成完整性门控：只有 `finish_reason=stop` 的响应才把 parser 结果送入正确性判定。`length` 等非正常结束响应即使从残缺正文提取出候选字符串，也只把该值保存在 `prediction.parser_candidate` 中用于审计，正式 `prediction.value` 置空并记为 `unverified`。这是为了避免把截断片段（例如几何推导中的线段名）误报为模型最终错答。

后续50题 high/4096 分层 baseline 的结果、成本和Asymptote输入问题见 `docs/experiments/BASELINE_50_FINDINGS.md`。
