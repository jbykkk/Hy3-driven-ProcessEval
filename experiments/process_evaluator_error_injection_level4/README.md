# Level 4受控过程错误探针

本实验复用25题v1/v2对照中`math-test-prealgebra-0485`的两条既有完整Solver解答，不重新调用Solver。构建脚本只修改可见`response.content`：把1错误地视为合数，随后一致地用`1,4,6,8`计算出乘积192和差18；每版分别保留正确最终答案1518或写入错误最终答案18。

生成4条受控输入与预期标签：

```bash
uv run python scripts/build_process_error_injection_probe.py
```

对本地输入重新运行答案验证和Process Evaluator后，聚合对照：

```bash
uv run python scripts/analyze_process_error_injection_probe.py
```

- `cases.jsonl`：来源inference、可见内容哈希、注入位置和预设结果；不含内部reasoning。
- `analysis.json`：逐例Evaluator判定、预期标签匹配、调用量与本地输出版本信息；不复制Solver正文或Evaluator内部reasoning。
- 完整解释见`docs/experiments/PROCESS_EVALUATOR_ERROR_INJECTION_LEVEL4.md`。

原始Evaluator响应、流事件、受控Solver输入和答案验证记录均位于被Git忽略的`outputs/`。
