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

这里的`reference_answer`是最终结论的标准答案，不是过程正确性的标准标注。即使`answer_correct=true`，可见解答仍可能包含相互抵消的错误、关键跳步或无法支持答案的断言；即使最终答案错误，也需要另行判断此前过程是否局部有效。因此该记录可以作为Process Aggregator的独立元数据，但不能用于给Local/Global过程判断自动贴标签。过程级有效性验证所需的人工标注见`PROCESS_EVALUATOR.md`。

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

这项分类用于说明验证器覆盖边界，不替代数学语义判断。当前优先可靠覆盖整数、分数、根式及普通单表达式；结构化答案进入人工复核。

## 生成完整性与验证边界

答案 parser 支持无显式 `Answer:` 标签的结论句、主要单位答案以及末尾数学表达式。评测入口同时执行生成完整性门控：只有 `finish_reason=stop` 的响应才进入正式正确性判定；其他结果即使能够提取候选字符串，也统一记为 `unverified`。

整数、分数、根式和普通单表达式可以直接进行数学等价判断。多答案、集合、区间、矩阵、单位和选择题标签等结构化答案通过 `manual_review_recommended` 进入人工复核，避免把表达格式差异直接计为答案错误。
