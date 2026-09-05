# 最终结果数据

本目录只保留三份正式报告直接使用的公开结果，不包含模型内部推理、Provider 原始响应、流式事件、请求标识、失败重试或历史版本实验记录。

## 文件说明

- `controlled_errors.jsonl`：16条人工注入错误案例。每条记录包含题目及来源链接、注入后的可见解答、人工首错与错误类型标签，以及 `high`、`low` 两种 Process Evaluator 配置的最终判断。
- `controlled_error_process_evaluations.jsonl`：上述16条案例对应的结构化 Local、Global 与确定性聚合结果，仅保留通过 schema 校验的可见评估内容。
- `regular_solutions_review.json`：常规解答验证集中45份 `low` Solver 解答的逐题人工过程标签、唯一过程错误的复核依据，以及需要人工确认的答案格式记录。
- `analysis_metrics.json`：Solver Prompt v1/v2对照、45题 Solver `high`/`low` 对照和16例 Process Evaluator `high`/`low` 对照的汇总指标。

题目正文和标准答案来自 [`data/benchmark/math_text.jsonl`](../data/benchmark/math_text.jsonl)。分析结论分别见 [`COMPLETE_RESULTS.md`](../reports/COMPLETE_RESULTS.md)、[`EVALUATOR_VALIDITY.md`](../reports/EVALUATOR_VALIDITY.md) 和 [`PROJECT_ANALYSIS_REPORT.md`](../reports/PROJECT_ANALYSIS_REPORT.md)。

## 数据边界

`controlled_errors.jsonl` 中的可见解答是人工注入错误后的受控输入，不计入 Solver 自然生成结果。`controlled_error_process_evaluations.jsonl` 中的 `evidence` 是 Process Evaluator 按固定 schema 输出的简要判断依据，不是模型内部 reasoning。`regular_solutions_review.json` 保存人工过程判断，不包含原始模型响应。`analysis_metrics.json` 只提供报告所需的聚合统计，不能用于还原模型内部推理。
