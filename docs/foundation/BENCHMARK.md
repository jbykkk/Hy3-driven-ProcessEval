# Benchmark 数据集组成与特征

## 1. 定位与总体组成

当前数据池用于项目第一阶段的 Hy3 数学解题流程，并为后续最终答案校验、过程正确性评估和错误定位提供基础题集。它由三个公开英文数学数据集的 test split 确定性抽样得到，共 400 题。

自2026-08-25起，主实验评测范围收敛为 MATH 250题，官方 Level 1-5各50题。GSM8K 100题和 AIME 50题不删除、不改写，暂时仅作为后续补充实验。除非实验 manifest 明确说明，后续“主 benchmark”默认指 `data/benchmark/math.jsonl`，而“完整数据池”指合并后的400题。

| 数据集 | 题数 | 占比 | 主要难度范围 | 抽样方式 |
| --- | ---: | ---: | --- | --- |
| GSM8K | 100 | 25% | 小学至初中基础应用题 | 从 `main/test` 中抽取100题，不添加难度标签 |
| MATH | 250 | 62.5% | 中学竞赛数学，官方 Level 1-5 | 每个 Level 独立抽取50题 |
| AIME | 50 | 12.5% | 高难度数学竞赛题 | AIME 2024、2025各抽取25题 |

所有样本均来自 test split，不使用训练集。抽样种子为 `20260824`，以“种子 + 稳定样本 ID”的 SHA-256 排序结果进行选择。该方法不依赖运行时随机状态；相同原始数据和参数会生成完全相同的文件。

当前题集具有以下整体性质：

- 400个样本 ID 全局唯一。
- 经过空白归一化后没有完全相同的题目；尚未执行语义级近重复检测。
- 三个数据集不强行映射到统一难度标尺，只保留各自有依据的难度信息。
- 题目均为英文，数学表达式主要使用 LaTeX；部分竞赛题包含 Asymptote 图形源码。
- `data/benchmark/benchmark.jsonl` 是三个子集的合并版本，顺序为 GSM8K、MATH、AIME。

## 2. 统一 JSONL 结构

每行表示一道题，公共字段如下：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `schema_version` | string | 当前数据结构版本，现为 `1.0` |
| `id` | string | 全局唯一、可复现的样本 ID |
| `dataset` | string | `gsm8k`、`math` 或 `aime` |
| `problem` | string | 保持原意的原始题目文本 |
| `reference_answer` | string | 从原始数据提取的最终标准答案 |
| `reference_solution` | string/null | 原始参考解答；来源没有过程解答时为 `null` |
| `metadata` | object | 数据源、revision、split、原始索引及数据集专属信息 |

`metadata` 中的公共溯源字段包括：

- `source_repo`：Hugging Face 数据仓库。
- `source_revision`：本次使用的固定 revision。
- `source_split`：当前均为 `test`。
- `source_index`：样本在对应原始文件内的索引。
- `difficulty`：数据集自身的难度信息；没有依据时为 `null`。

数据集专属信息不会被丢弃。例如 MATH 额外保留 `subject` 和 `source_config`，AIME 额外保留 `year`、`source_id`，2024题目还保留原始 URL。

## 3. GSM8K

### 3.1 数据来源与抽样

- 来源仓库：[`openai/gsm8k`](https://huggingface.co/datasets/openai/gsm8k)
- 配置与 split：`main/test`
- 原始 test 规模：1,319题
- 当前抽样规模：100题
- 数据许可标记：MIT

GSM8K 原始字段是 `question` 和 `answer`。整理时，`question` 映射为 `problem`，完整的 `answer` 保存为 `reference_solution`，最后一个 `####` 后的值提取为 `reference_answer`。

### 3.2 题目特征

- 以生活化文字应用题为主，通常通过若干步四则运算得到结果。
- 不含官方难度等级，因此当前 `difficulty` 为 `null`，没有进行人为分级。
- 当前100题的标准答案全部可以表示为普通整数。
- 当前样本题目长度约为84至596个字符，平均约243个字符；字符长度只反映文本规模，不代表推理难度。

参考解答中包含形如 `<<3*60=180>>` 的计算标注，并以 `#### 45` 标记最终答案。这使 GSM8K 很适合在早期验证以下能力：

- 多步计算过程能否完整输出；
- 中间算术是否正确；
- 最终答案能否通过整数精确匹配；
- 错误首次出现在哪一个计算步骤。

它的局限是题型和答案形式相对单一，不能充分检验符号推导、几何证明或复杂等价表达式。

## 4. MATH

### 4.1 数据来源与抽样

- 来源仓库：[`EleutherAI/hendrycks_math`](https://huggingface.co/datasets/EleutherAI/hendrycks_math)
- split：七个学科配置各自的 `test`
- 原始 test 总规模：5,000题
- 当前抽样规模：250题
- 数据许可标记：MIT

MATH 原始字段包括 `problem`、`solution`、`level` 和 `type`。本项目保留完整参考解答，并从最后一个可解析的 `\boxed{...}` 中提取 `reference_answer`。

### 4.2 难度分布

官方 Level 1-5被原样保留，每级严格抽取50题：

| 难度 | 题数 |
| --- | ---: |
| Level 1 | 50 |
| Level 2 | 50 |
| Level 3 | 50 |
| Level 4 | 50 |
| Level 5 | 50 |

这五个等级只用于 MATH 内部的分层分析，不直接等价于 GSM8K 或 AIME 的难度。

### 4.3 学科分布

抽样只对难度做了硬性分层，没有对学科数量做二次配额，因此学科分布来自确定性哈希抽样的自然结果。

| 学科 | 题数 |
| --- | ---: |
| Algebra | 61 |
| Prealgebra | 46 |
| Precalculus | 41 |
| Intermediate Algebra | 35 |
| Geometry | 23 |
| Number Theory | 23 |
| Counting & Probability | 21 |

难度与学科的交叉分布如下：

| 难度 | Algebra | Counting & Probability | Geometry | Intermediate Algebra | Number Theory | Prealgebra | Precalculus |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Level 1 | 13 | 4 | 7 | 3 | 3 | 8 | 12 |
| Level 2 | 5 | 6 | 5 | 7 | 4 | 11 | 12 |
| Level 3 | 18 | 3 | 3 | 5 | 5 | 10 | 6 |
| Level 4 | 11 | 5 | 7 | 7 | 7 | 9 | 4 |
| Level 5 | 14 | 3 | 1 | 13 | 4 | 8 | 7 |

### 4.4 答案与评测特征

- 250题均有完整参考解答。
- 164题的提取答案是普通整数。
- 其余86题包含分数、根式、区间、坐标、含 `\pi` 表达式、角度或选择题标记等形式。
- 当前样本题目长度约为21至718个字符，平均约170个字符。题目较短不代表难度较低，许多题依赖符号变换或竞赛技巧。

MATH 是当前 benchmark 中最适合分析“难度临界点”的部分，因为它同时具有官方五级难度、七类学科和完整过程解答。但它的最终答案不能普遍使用字符串精确匹配。例如 `1/2`、`0.5` 和 `\frac{1}{2}` 在数学上可能等价，后续校验器需要进行 LaTeX/符号规范化或数学等价性判断。

## 5. AIME 2024/2025

### 5.1 数据来源与抽样

| 年份 | 来源 | 原始题数 | 抽样题数 | 许可标记 |
| --- | --- | ---: | ---: | --- |
| 2024 | [`math-ai/aime24`](https://huggingface.co/datasets/math-ai/aime24) | 30 | 25 | Apache-2.0 |
| 2025 | [`math-ai/aime25`](https://huggingface.co/datasets/math-ai/aime25) | 30 | 25 | Apache-2.0 |

AIME 不映射到 MATH 的 Level，统一使用 `difficulty: "competition"` 表示其竞赛定位，具体年份单独保存在 `metadata.year`。

### 5.2 题目与答案特征

- 题目覆盖代数、数论、组合、几何等竞赛方向，但当前来源没有统一的学科字段。
- 50题的标准答案全部是整数，符合 AIME 数值答案的基本形式，最终答案自动校验相对直接。
- 当前样本题目长度约为80至1,734个字符，平均约395个字符，是三个子集中平均文本最长的一组。
- 部分题目含 Asymptote 图形源码。模型输入时应完整保留源码；若应用需要面向用户显示图形，则需要另行设计渲染或文本替代方案。

### 5.3 参考过程的限制

AIME 当前数据更适合验证最终答案和高难题能力，而不能直接作为完整的过程标注集：

- 抽中的25道 AIME 2024题虽然具有 `solution` 字段，但内容基本只有 `\boxed{答案}`，不包含详细推导。
- 抽中的25道 AIME 2025题没有参考过程，`reference_solution` 为 `null`。

因此，后续若要使用 AIME 验证首个错误步骤定位，需要补充人工审核的标准过程、可靠的分步参考解答，或设计不依赖单一参考路径的过程验证方法。

## 6. 三个子集的互补关系

| 维度 | GSM8K | MATH | AIME |
| --- | --- | --- | --- |
| 核心能力 | 多步基础应用计算 | 多学科符号与竞赛推理 | 高难竞赛推理 |
| 难度信息 | 无官方分级 | 官方 Level 1-5 | 按竞赛与年份保留 |
| 最终答案形式 | 当前均为整数 | 整数与多种符号表达混合 | 整数 |
| 参考过程 | 100题均有分步解答 | 250题均有完整解答 | 无可直接使用的详细过程 |
| 初期答案校验 | 整数精确匹配 | 需要数学等价性判断 | 整数/AIME格式校验 |
| 过程评估价值 | 适合检查逐步算术 | 适合检查推导、定理和条件 | 适合检验高难推理，但需补充过程标注 |

三者仍可形成从基础文字应用题、分级竞赛题到高难竞赛题的能力梯度，但当前不再要求组合运行：MATH 用于主实验，GSM8K 可补充基础算术链条，AIME 可补充高难推理。任何跨数据集结果都应明确标记为补充实验，不能与 MATH 主实验分母混合。

## 7. 当前限制与后续注意事项

- 当前400题是小规模初始 benchmark，结果不能代表模型在完整数据集上的总体能力。
- MATH 仅按 Level 分层，学科分布不是均匀配额；按学科比较时应同时报告样本量。
- 三个数据集的难度定义不同，不应直接把 GSM8K、MATH Level和AIME拼成一个未经验证的统一等级。
- 当前只检查了规范化文本的完全重复，尚未检测改写题、同源题或语义近重复。
- MATH 的最终答案需要比字符串比较更可靠的等价性校验。
- AIME 缺少详细参考推理，是后续过程评估设计中需要明确处理的数据缺口。
- benchmark schema 描述的是题目输入和标准参考信息；Hy3 模型响应与过程评估结果将使用独立的 JSONL schema，避免覆盖原始 benchmark。

数据源 revision、文件 SHA-256 和生成参数见 [`data/benchmark/manifest.json`](../../data/benchmark/manifest.json)，原始数据来源说明见 [`data/SOURCES.md`](../../data/SOURCES.md)。
