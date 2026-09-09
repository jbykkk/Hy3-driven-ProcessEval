# MATH Benchmark

本目录只保留项目当前使用的 MATH 数据。两份题集均来自 `EleutherAI/hendrycks_math` 固定 revision `21a5633873b6a120296cce3e2df9d5550074f4a3` 的 test split。

完整下载链接、命令和原始文件目录结构见 [`../SOURCES.md`](../SOURCES.md)。原始数据应放在 `data/raw/math_eleutherai/`，构建脚本会从七个学科子目录读取 `test-*.parquet`。

## 文件

- `math.jsonl`：原始分层抽样集，共250题，官方Level 1-5各50题；其中20道题的`problem`含Asymptote源码。
- `math_text.jsonl`：项目实际使用的纯文字候选集，共250题，Level 1-5各50题；保留`math.jsonl`的230道非图形题，并在相同Level确定性补入20道纯文字题。
- `manifest.json`：数据源revision、抽样种子、分层数量及两份题集的SHA-256。
- `math_text_manifest.json`：纯文字变体的逐层排除/替换ID及文件哈希。

每条JSONL记录包含题目、标准答案、上游参考解答、官方难度、学科和固定来源信息。Solver只读取`id`、`dataset`和`problem`，不会接收标准答案、参考过程或metadata。

## 抽样方法

抽样种子为`20260824`。在每个MATH Level内，按`SHA-256("<seed>:<stable-id>")`升序选择50题。纯文字变体保留不含`[asy]`的已选题，并从未进入`math.jsonl`的同Level纯文字test样本中使用相同排序规则补齐。

已提交文件可以直接运行本项目的Solver、答案验证和过程评估流程，无需保留`data/raw/`。若要从上游重新生成题集，应先按[原始数据来源与下载](../SOURCES.md)下载固定revision的数据，再运行：

```bash
uv run python scripts/build_benchmark.py
```
