# Process Evaluator 16例受控错误集 v1.1

本版本保留v1的16道源题和整体错误设计，只改写评估器可见的合成解答，移除直接承认错误的措辞和元叙述。人工复核后，复数遗漏分支案例的v1.1首错标签由Step 4修正为Step 5；v1原文在Step 4已明确执行遗漏，因此v1标签和结果保持不变。v1.1已完成独立评估与人工复核。

本地重建与检查：

```bash
uv run python scripts/build_process_evaluator_error_injection_16_v1_1.py
uv run python -m evaluation.runner \
  --input outputs/process_evaluator_error_injection_16_v1_1_solver.jsonl \
  --output outputs/process_evaluator_error_injection_16_v1_1_answer_verification.jsonl
uv run python scripts/analyze_process_evaluator_error_injection_16_v1_1.py
```

上述命令只构造数据、解析步骤并离线核验最终答案，不运行Process Evaluator。`analysis.json`记录对全部16条`response.content`的显式自我揭示短语扫描和人工语义复核；注入说明位于不可见元数据中，可以明确描述人工标签。

当前状态：`complete`。16/16题均完成完整Local/Global评估，3条`needs_review`也已完成人工裁决。复核结论见`human_review.json`，按修正后人工标签重算的结果见`evaluation_analysis.json`；聚合记录、原始Evaluator响应（含reasoning）和流式事件分别保存在被Git忽略的`outputs/process_evaluator_error_injection_16_v1_1_evaluations.jsonl`、`outputs/process_evaluator_error_injection_16_v1_1_responses.jsonl`和`outputs/process_evaluator_error_injection_16_v1_1_stream_events.jsonl`。

本轮计划调用95次，成功完成95次（79次Local、16次Global）。开始时发生16次沙箱网络连接失败，未产生模型响应或token；这些失败尝试仍保留在原始响应与流事件文件中，因此原始响应共111行，但有效评估调用仍为95次。

由于runner采用追加式断点续跑，聚合JSONL包含16条首次不完整记录和随后16条完整记录；`evaluation_analysis.json`按`inference_id`选取最后的完整记录，不能把JSONL行数当作样本数或有效调用数。

人工复核后的结果摘要：过程错误检出15/16，首错Step准确14/16，错误类型准确9/16，Local状态和重要性均15/15、Local类型8/15、Local来源14/15，Global状态16/16，`process_complete` 13/16，最终答案支持度16/16，答案—过程关系15/16。原始聚合仍有3条`needs_review`，其来源分别是最终答案位置无法由当前Step schema表示、人工gold修正并伴随Evaluator起点分歧、以及Local假阳性与Local/Global冲突；它们不应统一解释为Evaluator失败。
