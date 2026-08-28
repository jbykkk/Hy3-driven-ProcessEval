# 初始数学 Benchmark

本目录由 `scripts/build_benchmark.py` 从 `data/raw/` 中的固定数据版本确定性生成。

当前不计划对任何一个250题集合执行全量API评测。`math_text.jsonl`的250道纯文字题作为可复现候选池保留，其文件构成仍为官方Level 1-5各50题；具体实验只选择少量、明确记录选择规则的样本。原`math.jsonl`、GSM8K与AIME继续保留；`benchmark.jsonl`的400题组成和哈希不变，新增变体不计入这个历史数据池总数。

## 文件

- `gsm8k.jsonl`：GSM8K test split 抽取 100 题，不添加难度。
- `math.jsonl`：MATH test split 抽取 250 题，Level 1-5 各 50 题。
- `math_text.jsonl`：保留`math.jsonl`的230道非图形题，并从同一固定revision的test split按Level确定性补入20道纯文字题；Level 1-5仍各50题且不含`[asy]`。
- `math_text_manifest.json`：纯文字变体的基础文件哈希、筛选规则、逐层排除ID、替换ID和输出哈希。
- `aime.jsonl`：AIME 2024、2025 各抽取 25 题。
- `benchmark.jsonl`：以上三个文件按 GSM8K、MATH、AIME 顺序合并，共 400 题。
- `manifest.json`：数据源 revision、抽样规则、分层数量和文件校验和。

## JSONL Schema

每行是一个独立对象：

```json
{
  "schema_version": "1.0",
  "id": "全局唯一且稳定的样本 ID",
  "dataset": "gsm8k | math | aime",
  "problem": "原始题目文本",
  "reference_answer": "用于最终答案校验的标准答案",
  "reference_solution": "原始参考解答；来源未提供时为 null",
  "metadata": {
    "source_repo": "Hugging Face 仓库",
    "source_revision": "固定 revision",
    "source_split": "test",
    "source_index": 0,
    "difficulty": null
  }
}
```

`metadata` 允许保留数据集专属字段，例如 MATH 的 `subject`、AIME 的 `year` 和题目 URL。难度标签不跨数据集强行统一。

## 重新生成

```bash
uv run python scripts/build_benchmark.py
```

脚本会同时重建原400题数据池和纯文字MATH变体。纯文字替换只从未进入原`math.jsonl`、不含字面量`[asy]`且难度相同的test样本中选择。

“纯文字”严格指模型输入字段`problem`不含`[asy]`。上游有13条`reference_solution`附带解释性Asymptote插图；这些参考过程不会进入solver prompt，后续过程评估使用前需另行确定处理规则。
