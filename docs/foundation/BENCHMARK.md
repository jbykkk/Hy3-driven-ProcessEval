# MATH Benchmark 数据集组成与特征

## 1. 数据来源与定位

本项目只采用公开MATH数据集，来源为[`EleutherAI/hendrycks_math`](https://huggingface.co/datasets/EleutherAI/hendrycks_math)固定revision `21a5633873b6a120296cce3e2df9d5550074f4a3`的七个学科test split。上游test共5,000题，包含完整参考解答、最终答案、官方Level 1-5和学科标签。

仓库保留两份各250题的数据：

| 文件 | 定位 | 数量 | 分层 |
| --- | --- | ---: | --- |
| `math.jsonl` | 原始确定性分层抽样集 | 250 | Level 1-5各50题 |
| `math_text.jsonl` | Solver和正式实验使用的纯文字候选集 | 250 | Level 1-5各50题 |

`math.jsonl`保留原始选择结果，包括20道题面含Asymptote源码的题目。`math_text.jsonl`保留其中230道非图形题，再从同一固定revision、同一Level、未进入原抽样集的纯文字test题中补入20题。原始抽样集不被覆盖，因而历史选择和实际实验输入均可复查。

## 2. 确定性抽样

抽样种子为`20260824`。每个候选样本先生成稳定ID，再在各Level内部按下式的SHA-256值升序排列并选择前50题：

```text
SHA-256("<seed>:<stable-id>")
```

纯文字替换也采用相同排序方式。逐层排除与替换ID记录在`math_text_manifest.json`，两个文件的SHA-256记录在`manifest.json`。当前哈希为：

| 文件 | SHA-256 |
| --- | --- |
| `math.jsonl` | `6ddb04a0360ff93e467ac05467867a59ee612a5924156e27dd91fa5cbdc8cc6f` |
| `math_text.jsonl` | `007b163e212272059562bff67e314ad19a6506d44c5799677b94cd9dafea40da` |

## 3. JSONL结构

每行是一道独立题目，字段包括：

| 字段 | 含义 |
| --- | --- |
| `id` | 全局唯一、可复现的样本ID |
| `dataset` | 固定为`math` |
| `problem` | 原始题面 |
| `reference_answer` | 从最后一个可解析的`\boxed{...}`提取的标准答案 |
| `reference_solution` | 上游完整参考解答 |
| `metadata.source_repo/revision/split/index` | 固定来源信息 |
| `metadata.difficulty` | 官方Level 1-5 |
| `metadata.subject` | 上游数学学科标签 |

Solver的数据加载层只暴露`id`、`dataset`和`problem`，不会把标准答案、参考解答、难度或学科信息传给模型。

## 4. 难度与学科

MATH官方Level 1-5各保留50题。纯文字候选集的学科分布如下：

| 学科 | 题数 |
| --- | ---: |
| Algebra | 65 |
| Prealgebra | 44 |
| Precalculus | 39 |
| Intermediate Algebra | 37 |
| Number Theory | 25 |
| Counting & Probability | 24 |
| Geometry | 16 |

抽样只对难度设置硬性配额，未对学科设置配额，因此不应把不同学科的小样本结果直接解释为稳定能力排名。

## 5. 答案形态与限制

MATH答案覆盖整数、分数、根式、区间、坐标、含`\pi`表达式、矩阵、复数和多答案等形式，不能普遍使用字符串精确匹配。本项目使用数学等价性验证，并把集合、区间、矩阵、单位等结构化答案标记为建议人工复核。

“纯文字”仅表示实际模型输入字段`problem`不含`[asy]`。`math_text.jsonl`中仍有13条上游`reference_solution`包含解释性Asymptote代码，但参考解答不会进入Solver或Process Evaluator输入。

当前正式结果只使用候选集中的小规模分层样本，不能外推为Hy3在全部250题或MATH完整test split上的总体性能。完整来源和重建方式见根目录[`README.md`](../../README.md)。
