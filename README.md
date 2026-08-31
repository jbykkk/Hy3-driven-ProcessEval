# Hy3 数学过程评估与错误定位

本项目是“犀牛鸟开源实战任务”数学方向作品，目标是在最终答案验证之外，对 Hy3 的可见分步解答进行过程正确性判断、首个错误步骤定位、错误类型归类，并识别“答案正确但过程不能支持结论”的样本。

## 当前能力

项目已经跑通以下链路：

```text
分层数学题集
  -> Hy3 Solver生成可见分步解答
  -> 最终答案解析与数学等价验证
  -> 确定性Step Parser
  -> 逐步Local Process Evaluator
  -> 整体Global Process Evaluator
  -> 无LLM聚合、首错定位与答案—过程关系
```

- Solver输入边界阻止标准答案、参考解答和难度标签进入模型prompt。
- 原始模型响应、可见回答、内部reasoning、流事件、答案验证和过程评估分开保存。
- Process Evaluator只评价可见`response.content`，不读取Solver内部reasoning或参考解答。
- 最终答案正确性与过程正确性独立，可以输出`correct_answer_invalid_process`。
- 支持错误来源、固定错误类型、Local/Global冲突和人工复核状态。

## 当前主要结果

- 25题Solver prompt v1/v2配对：两版均25/25完整且答案正确；v2步骤减少24.5%，Evaluator总tokens减少17.7%，但Solver总tokens增加1.17%。
- 16例去提示化受控错误的新版分类评估：过程错误16/16、首错16/16、错误类型14/16、答案—过程关系16/16，`needs_review` 1/16。
- 同题45题Solver high/low对照：两种强度均45/45完整且答案正确；low total tokens为113,594，较high的311,089减少63.5%，并保留1例答案正确但过程错误的自然样本。
- 冻结新版prompt和同一16份受控错误解答后，Evaluator low相对high的错误检出从16/16降至13/16，首错从16/16降至14/16，类型均为14/16。

这些结果属于小规模、明确目的的阶段实验，不把不同配置、历史prompt或受控/自然错误混为一个总准确率。统一实验地图、指标口径和最终报告缺口见[项目实验与报告准备度](docs/experiments/PROJECT_RESULTS_READINESS.md)。

## 数据与实验范围

- `data/benchmark/math_text.jsonl`：纯文字MATH候选池250题，官方Level 1-5各50题；不做全量API调用。
- `data/benchmark/math.jsonl`：原MATH选择250题，含20道Asymptote题，完整保留。
- `data/benchmark/gsm8k.jsonl`：100题，作为补充候选。
- `data/benchmark/aime.jsonl`：2024/2025共50题，当前暂停评测。

原始下载数据、模型完整输出、内部reasoning、流事件、密钥和虚拟环境均不提交Git。可复现的选择、配置、聚合结果和人工复核材料保存在`experiments/`。

## 快速开始

环境使用`uv`管理，Python要求3.10及以上：

```bash
uv sync
cp .env.example .env
```

在本地`.env`配置`HY3_API_KEY`后，可先安全查看单题prompt而不调用API：

```bash
uv run python -m solver.runner --dry-run --id math-test-algebra-0024
```

运行单题Solver：

```bash
uv run python -m solver.runner --id math-test-algebra-0024
```

离线验证最终答案：

```bash
uv run python -m evaluation.runner
```

对已有完整inference安全查看过程评估输入：

```bash
uv run python -m process_evaluation.runner --dry-run --id math-test-algebra-0024
```

默认命令只处理一个目标；批量API调用、显式重跑和`--all`都会增加额度消耗，运行前应先核对样本范围与输出路径。

## 文档导航

- [Benchmark设计](docs/foundation/BENCHMARK.md)
- [Solver设计与CLI](docs/foundation/SOLVER.md)
- [答案验证](docs/foundation/ANSWER_VERIFICATION.md)
- [Process Evaluator设计](docs/foundation/PROCESS_EVALUATOR.md)
- [Baseline 50与生成预算问题](docs/experiments/BASELINE_50_FINDINGS.md)
- [Solver prompt v1/v2 25题对照](docs/experiments/PROCESS_EVALUATOR_V1V2_25.md)
- [16例受控错误与三轮评估](docs/experiments/PROCESS_EVALUATOR_ERROR_INJECTION_16.md)
- [Level 4/5 low 20题自然错误实验](docs/experiments/PROCESS_EVALUATOR_LOW_LEVEL45_20.md)
- [Solver与Evaluator推理强度对照](docs/experiments/PROCESS_EVALUATOR_REASONING_EFFORT_COMPARISON.md)
- [项目实验与报告准备度](docs/experiments/PROJECT_RESULTS_READINESS.md)
- [当前进展](PROJECT_PROGRESS.md)
- [后续待办](TODO.md)

## 当前完成边界

核心工程和阶段实验已经足以开始统一结果口径与总报告写作，但最终提交仍需补齐：自然valid样本的人工抽检、可公开逐样本结果索引、`final_answer`错误位置、正式结果报告、demo视频/GIF，以及明确的开源许可证。
