# Process Evaluator 45题候选池

本目录把两批已经完成的`math-solver-v2`解答整理为统一索引：

- 先前Level 1-5各5题中的25条v2 inference；
- 新增Level 4和Level 5各10题的20条v2 inference。

`index.jsonl`逐题记录Level、官方学科、来源批次、Solver输出路径、`inference_id`和最终答案验证结果。它不复制可见解答或内部reasoning；完整模型记录继续保存在被Git忽略的`outputs/`，并通过`inference_id`定点读取。

重建索引与新增20题聚合结果：

```bash
uv run python scripts/build_process_evaluator_candidate_pool.py
```

这45题是人工注入受控错误和改进Process Evaluator的候选池，不是现成的准确率benchmark。注入错误后仍需冻结修改后的可见解答、Step边界、预期首错位置和人工标签；官方参考答案不能替代逐步过程标注。
