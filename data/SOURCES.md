# 原始数据来源与下载

本项目当前正式评测只使用 MATH 数据集。原始文件来自 Hugging Face 上的
[`EleutherAI/hendrycks_math`](https://huggingface.co/datasets/EleutherAI/hendrycks_math)，并固定为 revision
`21a5633873b6a120296cce3e2df9d5550074f4a3`，避免上游更新导致题目或文件结构漂移。

原始数据应下载到仓库根目录下的 `data/raw/math_eleutherai/`。`data/raw/` 已被 Git 忽略，不应提交；确定性抽样产生的小规模题集保存在 `data/benchmark/` 并提交版本管理。

## 下载方法

先安装项目依赖：

```bash
uv sync
```

随后在仓库根目录执行：

```bash
uv run hf download EleutherAI/hendrycks_math \
  --repo-type dataset \
  --revision 21a5633873b6a120296cce3e2df9d5550074f4a3 \
  --local-dir data/raw/math_eleutherai
```

也可以直接使用项目依赖中的 `huggingface_hub`：

```bash
uv run python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='EleutherAI/hendrycks_math', repo_type='dataset', revision='21a5633873b6a120296cce3e2df9d5550074f4a3', local_dir='data/raw/math_eleutherai')"
```

下载完成后，构建脚本要求七个学科配置分别位于各自子目录，并读取其中的 `test-*.parquet`：

```text
data/raw/math_eleutherai/
├── algebra/test-00000-of-00001.parquet
├── counting_and_probability/test-00000-of-00001.parquet
├── geometry/test-00000-of-00001.parquet
├── intermediate_algebra/test-00000-of-00001.parquet
├── number_theory/test-00000-of-00001.parquet
├── prealgebra/test-00000-of-00001.parquet
└── precalculus/test-00000-of-00001.parquet
```

Hugging Face 仓库可能同时下载 README、元数据和 train split；构建脚本只读取上述七个学科的 test split，并校验总数为 5,000 题。

## 重新构建与校验

原始文件就位后，在仓库根目录运行：

```bash
uv run python scripts/build_benchmark.py
uv run python -m unittest tests.test_benchmark_builder -v
```

脚本会以固定种子 `20260824` 重建：

- `data/benchmark/math.jsonl`：Level 1-5 各 50 题；
- `data/benchmark/math_text.jsonl`：排除题面含 Asymptote 源码的样本，并在同一 Level 确定性补齐；
- 两份 manifest：记录来源 revision、选择规则、替换 ID 和 SHA-256。

预期哈希见 [`benchmark/README.md`](benchmark/README.md)。重新构建后不应修改原始下载目录。
