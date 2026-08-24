# 项目交接说明

本文面向完全没有历史上下文的新会话。开始工作前，请先阅读根目录的 `AGENTS.md`、`PROJECT_PROGRESS.md`，再根据任务查看 `docs/` 下的设计文档。

## 1. 项目与当前阶段

本项目是“犀牛鸟开源实战任务”的数学方向作品。开发分支为 `develop`，远程仓库为 `origin`。不要直接在 `main` 上开发。

当前处于阶段 1：基于腾讯混元 Hy3 API 跑通数学题分步解答、完整实验记录和最终答案验证。阶段 1 的生成与基础验证链路已经跑通；下一重点是增强结构化答案校验、处理生成截断，并扩大分层实验。更后续的目标才是过程正确性评估、首个错误步骤定位和错误类型归类。

初始 benchmark 共 400 题：

- GSM8K：100题，保留官方 test split 语义，不另加难度。
- MATH：250题，官方 Level 1-5 各50题。
- AIME：50题，2024和2025各25题，作为高难竞赛题，不映射到 MATH 等级。

统一数据位于 `data/benchmark/*.jsonl`，原始下载位于被 Git 忽略的 `data/raw/`。抽样种子为 `20260824`，构建结果已做两次确定性校验。

## 2. 已完成的主要实现

### Solver

已实现以下链路：

```text
benchmark.jsonl
  -> Dataset Loader（仅 id/dataset/problem）
  -> Prompt Builder（math-solver-v1）
  -> 独立 Hy3 Client
  -> 原始 API Response + Response Parser
  -> outputs/solver_outputs.jsonl
```

关键约束与能力：

- `solver/dataset.py` 从类型边界阻止 `reference_answer`、`reference_solution` 和 metadata 进入模型输入。
- `solver/client.py` 使用腾讯云 TokenHub 的 OpenAI-compatible Chat Completions API，默认模型为 `hy3`。
- API Key 只从环境变量或本地 `.env` 读取；持久化配置明确排除密钥。
- `solver/runner.py` 默认只调用1题；只有显式 `--all` 才会运行全部选中题目。
- 支持按 ID 选择、断点续跑、显式重复实验、重试、usage/耗时/错误记录。
- 每次 inference 保存独立 `run_id`/`inference_id`、可见回答、`reasoning_content`、安全响应头、SDK 解析后的原始响应和解析结果。
- solver 输出逐行追加；`outputs/` 被 Git 忽略，不会随仓库同步。

当前 parser 为 `solution-parser-v1.2`，已支持：

- 编号为 `Step 1, Step 2, ...` 的步骤提取；
- 嵌套 `\boxed{}`；
- Markdown `**Answer:**`；
- 无显式 Answer 标签的 `Therefore/Thus/Hence` 结论句；
- 货币和千位分隔符；
- 主要答案后附另一种单位；
- `\(...\)` 中多个等价表达的末尾答案。

### 最终答案验证

已新增独立验证层：

```text
solver_outputs.jsonl + benchmark reference_answer
  -> 用当前 parser 从原始回答重新提取
  -> exact match + math-verify/SymPy 数学等价验证
  -> outputs/answer_verification.jsonl
```

验证记录按 `inference_id` 生成，保留：

- `exact_match`
- `math_equivalent`
- `format_mismatch_but_equivalent`
- `manual_review_recommended`
- gold/prediction 的规范表达、验证器版本和错误原因

依赖为 `math-verify>=0.9.0,<1.0`，并启用官方建议的 ANTLR 4.13.2 解析支持。验证器当前优先可靠覆盖整数、分数、小数、根式、普通代数表达式和部分区间/集合。结构化答案即使自动判等，也应保留人工复核。

## 3. 已完成的真实 Hy3 验证

本地 `outputs/` 当前有13条 inference 验证记录：12条 `correct`，1条 `unverified`，其中5条为 `format_mismatch_but_equivalent`。这里的13条包含重复调用和一次截断后重试，不能当作13道独立题的模型准确率。

已验证的代表性格式：

| 场景 | 模型预测 | 参考答案 | 结论 |
| --- | --- | --- | --- |
| GSM8K 普通整数 | `45` | `45` | 正确 |
| MATH 根式空格差异 | `5 + 6\sqrt{2}` | `5+6\sqrt{2}` | 数学等价 |
| MATH 混合数写法 | `8\frac{4}{7}` | `8\frac47` | 均规范化为 `60/7` |
| GSM8K 货币/千位符 | 从 `\$1,596` 提取 `1596` | `1596` | 正确 |
| GSM8K 等价单位 | 优先提取 `180,000 meters`，忽略后述 `180 km` | `180000` | 正确 |
| MATH 分数/小数 | `0.5` | `\frac{1}{2}` | 数学等价 |
| MATH 区间 | `(-\infty,\,-3)` | `(-\infty, -3)` | 数学等价，需复核 |
| MATH 无序多根 | `-1,-\frac32,7` | `-\frac32,-1,7` | 集合等价，需复核 |

曾使用一题 AIME 做跨数据集 smoke test，答案204正确，但耗时约46.7秒、使用4071 tokens。AIME 当前50题参考答案全是整数，且推理成本高，不适合作为答案格式转换的日常迭代集。后续优先用 MATH 做多格式验证，GSM8K 做快速整数回归，AIME 只做阶段性高难验证。

一次 MATH 多根题在 `reasoning_effort=high`、`max_tokens=4096` 时将4096个 completion tokens 全部用于推理，返回 `finish_reason=length` 且可见回答为空。使用 `reasoning_effort=low` 重试后以1988 tokens 完成并验证正确。首次截断记录没有删除，仍作为 `unverified` 证据保留。

## 4. 新会话开始时的检查与常用命令

确认分支和工作区：

```bash
git branch --show-current
git status --short
```

环境由 `uv` 管理，虚拟环境为 `.venv/`：

```bash
uv sync
uv run python -m unittest discover -s tests -v
```

配置 API：复制 `.env.example` 为本地 `.env`，只填写本地密钥。`.env` 已被忽略，禁止提交或把密钥写入命令输出、日志、源码和数据。

安全查看单题 prompt，不调用 API：

```bash
uv run python -m solver.runner --dry-run --id gsm8k-test-0008
```

真实调用前必须确认题目数量和额度。指定单题：

```bash
uv run python -m solver.runner --id gsm8k-test-0008
```

重复同一道题会追加新 inference，必须显式关闭 resume：

```bash
uv run python -m solver.runner --id math-test-prealgebra-0023 --no-resume
```

重新验证所有本地 inference，不会调用 API：

```bash
uv run python -m evaluation.runner
```

由于 `outputs/` 不提交 Git，新机器或全新 clone 不会拥有上述13条实验记录；同一工作区的新会话仍可读取它们。文档中的实验结论已纳入版本管理。

## 5. 下一步建议顺序

1. 在 runner 中显式处理 `finish_reason=length`：保留首次证据，记录截断状态，并提供受控、可审计的低 reasoning 或更大 token 重试策略。不要静默覆盖原记录，也不要无限重试。
2. 给参考答案和预测答案增加答案类型分类，逐类实现多答案、集合、区间、坐标、矩阵、单位、选择题标签和复数校验；先用合成对测试，再做少量真实 API 实验。
3. 扩大 GSM8K/MATH 分层样本，统计独立题目正确率、parser 提取成功率、等价格式率、截断率和人工复核率。重复 inference 必须与独立题目分开统计。
4. 实现按固定 Hugging Face revision 下载原始数据的可复现脚本。目前 revision 已记录、benchmark 可复现，但下载步骤还未脚本化。
5. 最终答案链路稳定后，再开始过程步骤正确性、首错定位和错误类型设计。

## 6. 已知风险与安全边界

- **API 消耗风险**：`--all` 会运行所有待处理题；真实调用前必须先用 `--dry-run` 或精确 `--id` 检查范围。默认重试最多2次，也会增加额度消耗。
- **截断误判风险**：当前 runner 会把HTTP成功但 `finish_reason=length` 的响应记为 `status=success`；验证层会因无答案给出 `unverified`，但 runner 尚无专门截断状态或自适应重试。
- **推理预算风险**：high reasoning 对简单题不一定更好，可能占满输出预算。不能简单地全局提高 `max_tokens`，否则成本和延迟会明显上升。
- **验证器误判风险**：`math-verify` 和当前正则启发式不是完整数学证明器。多根、集合、区间、矩阵、单位、选择题和含自然语言的答案必须保留类型化规则和人工抽检。
- **parser 启发式风险**：当回答同时给出多个等价单位或多个数学片段时，当前 parser 使用“主要加粗答案”或“最后数学片段”等规则；输出顺序异常时仍可能选错。
- **统计风险**：重复调用、失败重试和历史截断不能直接按行数计算题目正确率；应按 sample ID、inference ID 和实验配置分别统计。
- **密钥风险**：真实 `.env` 只应存在本机且已被 `.gitignore` 排除。`.env.example` 的 Key 必须保持为空。提交前仍需执行 secret audit。
- **输出数据风险**：`outputs/solver_outputs.jsonl` 保存完整模型响应、推理字段、request ID、用量和实验配置。虽然不含 API Key，仍不应未经审查公开；`outputs/` 必须继续保持忽略。
- **原始数据风险**：`data/raw/`、Hugging Face 缓存、虚拟环境和缓存文件不能提交。只提交可复现的小规模 `data/benchmark/`。
- **派生文件覆盖**：`evaluation.runner` 会重写 `outputs/answer_verification.jsonl`；solver 原始输出采用追加方式，不受影响。

## 7. 关键文件导航

- `AGENTS.md`：项目约束与记录规则。
- `PROJECT_PROGRESS.md`：简洁阶段进展和下一关键目标。
- `PROJECT_LOG.md`：追加式实施与实验日志。
- `docs/BENCHMARK.md`：benchmark 组成、来源和特征。
- `docs/SOLVER.md`：solver 架构、配置和输出 schema。
- `docs/ANSWER_VERIFICATION.md`：验证设计、答案形态审计与真实实验结果。
- `solver/runner.py`：调用入口、选择、resume、重试和落盘。
- `solver/client.py`：独立 Hy3 API client 与安全持久化配置。
- `solver/parser.py`：当前答案/步骤 parser。
- `evaluation/answer_verifier.py`：数学等价判断和人工复核标记。
- `evaluation/runner.py`：连接 inference 与 benchmark 参考答案并生成验证 JSONL。
- `tests/`：solver、parser 和验证器测试。

## 8. 当前验证状态

收工前执行的本地验证应为：15项单元测试通过，Python compileall 通过，`git diff --check` 无错误。若新会话观察到不同结果，应先检查依赖锁文件、Python版本和工作区状态，不要直接批量重跑 API。
