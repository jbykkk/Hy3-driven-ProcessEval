# Process Evaluator 统一受控错误池

本目录用统一索引汇总两个保持独立的实验：

- 旧Level 4概念错误探针：同一道源题的v1/v2与正确/错误最终答案共4个变体，已经运行Process Evaluator；
- 新16例分层受控错误集：16道不同源题，已完成构造、离线答案验证和首轮Process Evaluator评估。

合计为20个案例、17道不同源题，当前20例均已有Evaluator结果。`index.jsonl`逐例引用各自实验结果。不能把“20个案例”写成“20道题”，也不能把旧4例结果与新16例在不同提示词口径和构造限制下直接混成一个无说明分数。

重建索引：

```bash
uv run python scripts/build_process_evaluator_controlled_error_pool.py
```

原实验文件和本地输出均不移动、不覆盖；统一池只是来源与状态索引。
