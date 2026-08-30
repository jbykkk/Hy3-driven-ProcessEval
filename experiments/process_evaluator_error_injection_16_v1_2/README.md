# Process Evaluator 16例受控错误集 v1.2

本实验使用新版错误分类 prompt 对已完成人工复核的 v1.1 16例受控错误解答重新评估。题目、Solver 可见解答和评估流程均保持不变；仅使用新版分类 prompt，评估输出与原始响应写入独立 v1.2 路径，不覆盖 v1 或 v1.1。模型调用完成后，全部16例人工标签再按新版分类边界独立复核，形成v1.2人工标签。

Solver可见解答来源为`experiments/process_evaluator_error_injection_16_v1_1/cases.jsonl`；新版人工标签保存在本目录`cases.jsonl`，逐例复核记录为`taxonomy_review.json`。先前3条首错与schema裁决继续引用`experiments/process_evaluator_error_injection_16_v1_1/human_review.json`。

运行配置：Hy3、Local `math-process-evaluator-v1.1`、Global `math-global-evaluator-v1.2`、temperature 0.1、top-p 1、high reasoning、`max_tokens=8000`、300秒timeout、自动重试0次。首轮有16次沙箱连接失败；之后14道目标首轮完成，2道目标显式重试后完成。因此共有106次成功API响应（105次Local、17次Global）和16次失败尝试，共122条原始响应记录。

运行命令（结果已存在，不需要再次运行）：

```bash
uv run python -m process_evaluation.runner \
  --input outputs/process_evaluator_error_injection_16_v1_1_solver.jsonl \
  --answer-verification outputs/process_evaluator_error_injection_16_v1_1_answer_verification.jsonl \
  --output outputs/process_evaluator_error_injection_16_v1_2_evaluations.jsonl \
  --raw-output outputs/process_evaluator_error_injection_16_v1_2_responses.jsonl \
  --stream-events-output outputs/process_evaluator_error_injection_16_v1_2_stream_events.jsonl \
  --all --retry-incomplete --max-retries 0
```

最终汇总见`evaluation_analysis.json`。按新版人工复核标签，过程错误检出16/16，首错Step 16/16，错误类型14/16，Local状态15/15、重要性15/15、类型13/15、来源15/15，Global状态16/16，`process_complete` 13/16，最终答案支持度16/16，过程正确16/16，答案—过程关系16/16，`needs_review` 1/16。

本轮共使用353,599 total tokens（134,182 reasoning tokens），累计调用延迟约1,387.4秒。最初直接沿用v1.1标签得到的11/16只作为复核前过渡统计，不作为v1.2最终分类指标。人工复核依据新版定义独立进行，并非把标签改成模型预测：13条保持不变，3条修订，仍保留2条模型分类错误。

与 v1.1 相比，首错从14/16提高到16/16，错误检出从15/16提高到16/16，`needs_review`从3/16降到1/16。错误类型在各自版本人工标签下由9/16变为14/16，但两版分母的标签边界不同，不能把这5点全部解释为模型改善。剩余两条分类偏差是：`invalid_derivation`被判为`calculation_error`，以及`condition_omission`被判为`answer_extraction_or_format_error`。这些结果仍是人工构造受控样本上的行为验证，不代表自然错误上的准确率。

离线重算命令（不调用API）：

```bash
uv run python scripts/build_process_evaluator_error_injection_16_v1_2_labels.py
uv run python scripts/analyze_process_evaluator_error_injection_16_results.py \
  --cases experiments/process_evaluator_error_injection_16_v1_2/cases.jsonl \
  --evaluations outputs/process_evaluator_error_injection_16_v1_2_evaluations.jsonl \
  --responses outputs/process_evaluator_error_injection_16_v1_2_responses.jsonl \
  --analysis experiments/process_evaluator_error_injection_16_v1_2/evaluation_analysis.json \
  --experiment process-evaluator-error-injection-16-v1.2 \
  --expected-successful 106 \
  --local-prompt math-process-evaluator-v1.1 \
  --global-prompt math-global-evaluator-v1.2 \
  --annotation-version error-taxonomy-v1.2-human-reviewed \
  --taxonomy-review experiments/process_evaluator_error_injection_16_v1_2/taxonomy_review.json
```

被 Git 忽略的输出文件：

- `outputs/process_evaluator_error_injection_16_v1_2_evaluations.jsonl`
- `outputs/process_evaluator_error_injection_16_v1_2_responses.jsonl`
- `outputs/process_evaluator_error_injection_16_v1_2_stream_events.jsonl`
