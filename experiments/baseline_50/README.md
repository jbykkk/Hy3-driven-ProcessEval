# Baseline 50 实验材料

本目录保存可提交、可复查的实验定义和分析，不保存完整 provider 原始响应或 reasoning 正文。

- `manifest.json`：分层目标、种子、样本ID和选择文件校验和。
- `selection.jsonl`：50条完整 benchmark 记录。
- `analysis.json`：聚合结果、token/耗时、数据集与难度统计。
- `issues.jsonl`：23条截断与8条 parser v1.2 问题记录。
- `high_16000_selection.jsonl` / `high_16000_manifest.json`：23条截断样本的受控重跑定义，只将输出上限提高到16000。
- `high_16000_partial_analysis.json`：用户暂停时已完成16题的聚合结果；12题恢复、4题仍截断，剩余7题无本轮记录。
- `high_16000_partial_issues.jsonl`：4条16000仍截断记录和1条parser警告；不复制完整reasoning正文。

重新生成确定性选择：

```bash
uv run python scripts/build_baseline50.py
```

完整 API 输出只存在于被 Git 忽略的本地文件：

```text
outputs/baseline_50_solver_outputs.jsonl
outputs/baseline_50_answer_verification.jsonl
```

在本地输出存在时重新验证和生成分析：

```bash
uv run python -m evaluation.runner \
  --benchmark experiments/baseline_50/selection.jsonl \
  --input outputs/baseline_50_solver_outputs.jsonl \
  --output outputs/baseline_50_answer_verification.jsonl
uv run python scripts/analyze_baseline50.py
uv run python scripts/analyze_high16000_partial.py
```

人类可读结论、问题状态和后续决策见 `docs/experiments/BASELINE_50_FINDINGS.md`。
