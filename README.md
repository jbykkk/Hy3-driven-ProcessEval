# HyLLM Math Evaluator

基于腾讯混元 Hy3 的可验证数学推理与过程评估项目。系统不仅校验模型的最终答案，还会审查可见的分步解题过程，定位最早出现的主要错误、归纳错误类型，并识别“答案正确但推理过程不能支持结论”的样本。

> 本项目为腾讯2026犀牛鸟开源项目，非腾讯官方项目仓库，请注意甄别。官方Hy3仓库为：https://github.com/Tencent-Hunyuan/Hy3

本项目面向竞赛数学与数学文字题，将完整流程拆分为三个相互独立的阶段：

```text
分层 Benchmark
    -> Hy3 Solver：生成可见的分步解答与最终答案
        |-> Answer Verifier：确定性校验最终答案
        `-> Process Evaluator：逐步审查、首错定位、错误分类与全局聚合
```

Solver 不接收标准答案或参考解答；Process Evaluator 只评估 Solver 公开输出的数学过程，不读取模型内部 reasoning。最终答案正确性与过程正确性分别计算，从而避免以正确答案代替对推理有效性的判断。

## 主要功能

- **Hy3 数学求解**：调用 OpenAI-compatible Hy3 API，生成连续编号的 `Step 1, Step 2, ...` 解题过程和独立的 `Final Answer`。
- **安全、可恢复的批量运行**：支持单题、指定题目、限量或全量运行，逐条写入 JSONL，并记录生成完成状态、用量与流式事件。
- **最终答案验证**：使用独立验证器进行精确匹配和数学等价性判断，兼容常见分数、小数、根式及代数表达式。
- **过程正确性评估**：通过逐步 Local Evaluator、整体 Global Evaluator 和确定性聚合器判断可见推理链是否成立。
- **错误定位与分类**：定位最早的主要错误步骤，并覆盖题意误读、条件遗漏、分支遗漏、定理误用、无效推导、计算错误、依据不足和答案格式错误等类型。
- **答案—过程关系识别**：区分答案与过程均正确、答案错误且过程错误，以及答案正确但过程无效等情况。
- **分层评测与有效性验证**：提供按 MATH Level 1–5 分层的候选题集、常规解答人工复核记录及受控错误验证集。

实现细节见：

- [Solver 设计](docs/foundation/SOLVER.md)
- [最终答案验证设计](docs/foundation/ANSWER_VERIFICATION.md)
- [Process Evaluator 设计](docs/foundation/PROCESS_EVALUATOR.md)
- [Benchmark 设计](docs/foundation/BENCHMARK.md)

项目结果报告见：

- [完整结果报告](reports/COMPLETE_RESULTS.md)
- [Evaluator 有效性验证](reports/EVALUATOR_VALIDITY.md)
- [项目分析报告](reports/PROJECT_ANALYSIS_REPORT.md)

## 环境配置

### 系统要求

- Python 3.10 或更高版本
- [uv](https://docs.astral.sh/uv/)（推荐，用于依据 `uv.lock` 创建可复现环境）
- 可访问腾讯云 TokenHub 的 Hy3 API 凭证（仅真实调用 Solver 和 Process Evaluator 时需要）

项目运行依赖声明在 `pyproject.toml`，锁定版本记录在 `uv.lock`。安装依赖：

```bash
uv sync
```

复制环境变量样例，并填入本地 API Key：

```bash
cp .env.example .env
```

`.env` 的配置格式如下：

```dotenv
HY3_API_KEY="your-tokenhub-api-key"
HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
HY3_MODEL="hy3"
```

其中只有 `HY3_API_KEY` 必须由使用者提供；Base URL 和模型名称已有默认值。`.env` 已被 Git 忽略，不应提交真实凭证。已在 Shell 中设置的同名环境变量优先于 `.env`。

无需访问 API 即可运行全部单元测试：

```bash
uv run python -m unittest discover -s tests -v
```

## 快速开始

可以先列出适合快速开始的 Level 2 或 Level 3 题目（Level 4 和 5 的题目均可，但是对应推理时间更长、消耗的 token 也会相应增加）：

```bash
uv run python -m application list --level 2 --limit 5
uv run python -m application list --level 3 --limit 5
```

使用 `--dry-run` 检查所选题目，不产生 API 调用：

```bash
uv run python -m application run \
  --id math-test-algebra-0278 \
  --dry-run
```

配置 `HY3_API_KEY` 后，用一个命令运行完整流程：

```bash
uv run python -m application run \
  --id math-test-algebra-0278
```

### 推理强度参数

Solver 与 Process Evaluator 的推理强度可以分别设置：

| 参数 | 作用 | 可选值 | 默认值 |
| --- | --- | --- | --- |
| `--solver-reasoning-effort` | 控制 Hy3 生成数学解答时的推理强度 | `low`、`high` | `high` |
| `--evaluator-reasoning-effort` | 控制 Hy3 检查推理步骤、定位错误和进行全局评估时的推理强度 | `low`、`high` | `high` |

两个参数相互独立。例如，以下命令让 Solver 使用较低推理强度生成答案，同时让 Process Evaluator 使用较高推理强度进行审查：

```bash
uv run python -m application run \
  --id math-test-algebra-0278 \
  --solver-reasoning-effort low \
  --evaluator-reasoning-effort high
```

Hy3 TokenHub 接口当前支持 `low` 和 `high` 两档 `reasoning_effort`，不支持 `max`。提高推理强度通常会增加运行时间和 token 消耗。

Process Evaluator 会对每个可见步骤分别进行一次 Local Evaluation，随后再进行一次 Global Evaluation，因此较长的解答或较高的 Evaluator 推理强度可能显著增加总调用成本。

正式评测和 Demo 默认推荐使用 `high`；比较不同推理预算时，可以分别调整这两个参数。若两个参数都采用默认的 `high`，则无需在命令中显式填写。

## 过程、结果展示和保存

CLI 会依次展示题目、Solver 的完整可见解答、答案校验、每一个步骤的 Local Evaluation、Global Evaluation 和最终聚合结论。每次运行的完整记录保存在独立目录：

```text
outputs/runs/<run-id>/
├── solver.json
├── solver_stream_events.jsonl
├── answer_verification.json
├── process_evaluation.json
├── process_evaluator_responses.jsonl
├── process_evaluator_stream_events.jsonl
└── summary.json
```

`application.service.run_benchmark_case` 是与终端展示解耦的应用服务接口，并通过结构化事件回调报告各阶段结果。后续 Web UI 可以直接复用该接口，无需执行或解析 Shell 命令。

## 数据来源

项目采用公开的[MATH](https://huggingface.co/datasets/EleutherAI/hendrycks_math)数据集作为可验证数学推理场景，使用其`test split`中的题目、标准答案、参考解答、官方难度和学科标签。MATH数据集覆盖代数、几何、数论、计数与概率、预代数、预微积分和中级代数，并提供Level 1-5难度分层。

仓库保留两份各250题的数据：

- `data/benchmark/math.jsonl`：原始分层题集，Level 1-5各50题，用于保留最初的数据选择和题目来源。
- `data/benchmark/math_text.jsonl`：项目实际使用的纯文字候选集，Level 1-5各50题，不包含需要渲染Asymptote图形的题面。

### 数据集使用

正式Solver对照实验从纯文字候选集中选取45题，其中Level 1-3各5题、Level 4-5各15题。项目还基于同一题集构造16例受控错误过程，用于验证错误检出、首错定位和错误类型分类。更详细的数据结构与实验边界见[Benchmark设计](docs/foundation/BENCHMARK.md)。

实验采用纯文字的题目是为了更加适配 Hy3 纯文本大语言模型的输入形式，以及推理过程评估要求。

当前系统以文本形式向模型提供数学问题，直接输入MATH数据集中用于描述图形中数据关系 Asymptote 源码不能保证模型获得与原始渲染图一致的视觉信息。此类样本的错误可能同时来源于图形表示解析和数学推理，从而引入额外混杂因素，不利于对数学推理及错误定位能力进行独立评估。

Solver和应用CLI默认读取`math_text.jsonl`，并且只把题目正文传给Hy3，不向模型提供标准答案、参考解答、难度或学科信息。

MATH数据集的标准答案只由独立答案验证器（Answer Verifier）使用；题目难度用于分层结果分析;参考解答可辅助人工复核，但不会作为Process Evaluator的输入。

## License

本项目原创代码与文档采用 [MIT License](LICENSE) 开源协议，MATH数据仍遵循其上游许可条款。
