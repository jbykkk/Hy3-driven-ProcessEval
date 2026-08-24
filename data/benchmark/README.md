# 初始数学 Benchmark

本目录由 `scripts/build_benchmark.py` 从 `data/raw/` 中的固定数据版本确定性生成。

## 文件

- `gsm8k.jsonl`：GSM8K test split 抽取 100 题，不添加难度。
- `math.jsonl`：MATH test split 抽取 250 题，Level 1-5 各 50 题。
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
