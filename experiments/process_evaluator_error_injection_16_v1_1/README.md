# Process Evaluator 16例受控错误集 v1.1

本版本保留v1的16道源题、错误位置、错误类型和答案—过程关系，只改写评估器可见的合成解答，移除直接承认错误的措辞和元叙述。已经评估过的v1及其结果保持不变；v1.1已完成独立评估。

本地重建与检查：

```bash
uv run python scripts/build_process_evaluator_error_injection_16_v1_1.py
uv run python -m evaluation.runner \
  --input outputs/process_evaluator_error_injection_16_v1_1_solver.jsonl \
  --output outputs/process_evaluator_error_injection_16_v1_1_answer_verification.jsonl
uv run python scripts/analyze_process_evaluator_error_injection_16_v1_1.py
```

上述命令只构造数据、解析步骤并离线核验最终答案，不运行Process Evaluator。`analysis.json`记录对全部16条`response.content`的显式自我揭示短语扫描和人工语义复核；注入说明位于不可见元数据中，可以明确描述人工标签。

当前状态：`complete`。16/16题均完成完整Local/Global评估。评估结果见`evaluation_analysis.json`；聚合记录、原始Evaluator响应（含reasoning）和流式事件分别保存在被Git忽略的`outputs/process_evaluator_error_injection_16_v1_1_evaluations.jsonl`、`outputs/process_evaluator_error_injection_16_v1_1_responses.jsonl`和`outputs/process_evaluator_error_injection_16_v1_1_stream_events.jsonl`。

本轮计划调用95次，成功完成95次（79次Local、16次Global）。开始时发生16次沙箱网络连接失败，未产生模型响应或token；这些失败尝试仍保留在原始响应与流事件文件中，因此原始响应共111行，但有效评估调用仍为95次。

由于runner采用追加式断点续跑，聚合JSONL包含16条首次不完整记录和随后16条完整记录；`evaluation_analysis.json`按`inference_id`选取最后的完整记录，不能把JSONL行数当作样本数或有效调用数。

结果摘要：过程错误检出15/16，首错Step准确15/16，错误类型准确9/16，Global状态准确16/16，最终答案支持度准确16/16，答案—过程关系准确15/16；3条需要人工复核。分类偏差主要是相邻类型边界，不代表v1旧结果的自我揭示偏差。
