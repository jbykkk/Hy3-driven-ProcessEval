# Process Evaluator v1/v2 25题分层对照

本实验从`data/benchmark/math_text.jsonl`按固定种子`20260828`选择MATH Level 1-5各5题，共25题。同一选择分别使用`math-solver-v1`与`math-solver-v2`各生成一次，再独立执行最终答案验证和Process Evaluator v1。

`selection.jsonl`和`manifest.json`由以下命令确定性生成：

```bash
uv run python scripts/build_process_prompt_comparison.py
```

选择规则、源文件哈希、逐层ID和选择文件哈希见`manifest.json`。先前单题probe使用的`math-test-algebra-0144`被排除，避免把用于初步设计的样本重复计入本轮25题结果。

模型原始响应、内部reasoning、流事件和逐条过程评估位于被Git忽略的`outputs/`，不放入本目录。本目录中的`analysis.json`保存配置、输出文件哈希、分层与配对聚合统计，不复制任何reasoning或可见解答正文；解释性结论维护在`docs/experiments/PROCESS_EVALUATOR_V1V2_25.md`。

重新聚合当前本地输出：

```bash
uv run python scripts/analyze_process_prompt_comparison.py
```
