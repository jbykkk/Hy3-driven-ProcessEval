# Process Evaluator 候选池：Level 4/5 新增20题

本实验从纯文字MATH候选池选择Level 4和Level 5各10题，使用`math-solver-v2`各生成一次可见解答。选择明确排除先前v1/v2 25题，并在每个Level内优先覆盖所有可用的官方学科，再均衡补足到10题。

确定性重建选择：

```bash
uv run python scripts/build_process_evaluator_level45_20.py
```

Solver调用使用stream、high reasoning、`max_tokens=32000`、300秒timeout和0次自动重试。原始响应、内部reasoning与流事件写入被Git忽略的`outputs/process_v2_level45_20_solver*.jsonl`，不覆盖历史输出。

新增20题完成后，使用先前25题的v2 inference与本轮20题的v2 inference组成45题过程评估候选池。候选池首先用于人工注入受控错误与评估Evaluator，不直接作为Evaluator准确率benchmark；正式准确率结论仍需要冻结可见解答并建立独立人工标注。
