# Process Evaluator 16例受控错误集

本数据集从45题v2 Solver候选池中选择16道不同源题并定点注入错误：Level 1-3各2道，Level 4-5各5道。其中Level 4和Level 5各有1例保留正确最终答案但破坏关键推导；其余14例对应Level 1-3各2例、Level 4-5各4例。

错误覆盖8个固定类型，不使用兜底`other`：题意误解、概念或定理错误、非法推导、计算错误、条件遗漏、case遗漏、关键依据不足、答案提取或格式错误。每例只设计一个源头错误；后续使用错误结果的步骤应标为`error_origin=inherited`，不重复计作首错。

重建命令：

```bash
uv run python scripts/build_process_evaluator_error_injection_16.py
uv run python -m evaluation.runner \
  --input outputs/process_evaluator_error_injection_16_solver.jsonl \
  --output outputs/process_evaluator_error_injection_16_answer_verification.jsonl
uv run python scripts/analyze_process_evaluator_error_injection_16.py
```

- `cases.jsonl`保存来源inference、注入说明、预期首错标签和答案—过程关系，不复制内部reasoning。
- `analysis.json`保存构造校验、错误类型分布、答案验证匹配和逐例Step编号，不包含Evaluator预测。
- 完整注入后可见解答位于被Git忽略的`outputs/process_evaluator_error_injection_16_solver.jsonl`；记录是合成受控输入，不冒充真实provider响应，`reasoning_content`为空。
- `evaluation_analysis.json`保存首轮95次Process Evaluator调用与人工预期的逐项对照；Evaluator预测与`cases.jsonl`预期标签保持分离，不回写人工标签。
- 首轮评估已经完成，但若干注入步骤含自我揭示错误的措辞，结果只能作为受控行为探针；限制与异常案例见实验报告。
