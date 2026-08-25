# 项目交接说明

本文面向完全没有历史上下文的新会话。开始工作前，请先阅读根目录的 `AGENTS.md`、`PROJECT_PROGRESS.md` 和 `docs/experiments/BASELINE_50_FINDINGS.md`，再根据任务查看其他设计文档。

## 1. 项目与当前阶段

本项目是“犀牛鸟开源实战任务”的数学方向作品。开发分支为 `develop`，远程仓库为 `origin`。不要直接在 `main` 上开发。

当前处于阶段 1：基于腾讯混元 Hy3 API 跑通数学题分步解答、完整实验记录和最终答案验证。生成与基础验证链路已经跑通；当前正在冻结MATH主实验的输入、输出预算、截断处理和评分协议，不应直接启动250题全量调用。更后续的目标才是过程正确性评估、首个错误步骤定位和错误类型归类。

已整理的数据池共400题，但当前主实验只使用MATH：

- MATH：250题，官方 Level 1-5 各50题，是当前主实验评测集。
- GSM8K：100题，保留官方 test split 语义，不另加难度；仅作后续补充实验。
- AIME：50题，2024和2025各25题；暂时停止评测，仅保留为后续补充。

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

当前 parser 为 `solution-parser-v1.3`，已支持：

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

评测层现在先检查生成完整性：只有 `finish_reason=stop` 才进入正确性判定。截断响应中的 parser 候选会保留用于审计，但正式预测置空并标记为 `unverified`，避免把残缺推导误报为模型错答。

## 3. 已完成的真实 Hy3 验证

早期smoke test、跨数据集调用和答案格式验证已经证明solver与验证链路可用。50题high/4096 baseline的关键结果是27题完整、23题截断，端到端可验证答案产出率54%；全部HTTP请求均成功，因此主要瓶颈是生成预算而非API稳定性。

对截断题的high/16000对照在完成16/23题后暂停：12题恢复、4题仍截断，token消耗约为同样本4096轮的2.45倍。详细分层、成本、答案格式案例和机器可读材料索引统一见 `docs/experiments/BASELINE_50_FINDINGS.md`。

完整provider响应仍只存在于被Git忽略的`outputs/`。AIME当前暂停，GSM8K只作补充；除非用户重新授权，不要继续这些数据集的API调用。

## 4. 当前问题和处理边界

| 未决问题 | 当前边界 |
| --- | --- |
| 生成预算 | 4096不足、16000仍可能截断且成本高；不自动运行24000 |
| 图形输入 | 当前只传Asymptote源码文本；20道MATH图形题需单独协议和报告 |
| resume语义 | `length`会被当作成功记录跳过；修复前使用独立清单和输出文件 |
| 正式评测协议 | 尚需确定结构化答案、temperature/seed、批次和额度上限 |

截断误评分和parser v1.2主要问题已经解决，状态见合并报告。当前明确不做分段回答、记忆系统和24000测试。

## 5. 新会话开始时的检查与常用命令

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
uv run python -m solver.runner --dry-run --id math-test-algebra-0024
```

真实调用前必须确认题目数量和额度。指定单题：

```bash
uv run python -m solver.runner --id math-test-algebra-0024
```

重复同一道题会追加新 inference，必须显式关闭 resume：

```bash
uv run python -m solver.runner --id math-test-prealgebra-0023 --no-resume
```

重新验证所有本地 inference，不会调用 API：

```bash
uv run python -m evaluation.runner
```

由于 `outputs/` 不提交 Git，新机器或全新 clone 不会拥有早期13条或本轮50条完整 inference；同一工作区的新会话仍可读取它们。可公开复查的选择、聚合统计、异常形态和实验结论已纳入版本管理。

## 6. 下一步建议顺序

1. 修正solver完成状态和resume语义，避免把`finish_reason=length`当作已完成，同时保留请求成功事实。
2. 明确20道MATH `[asy]`图形题策略；当前输入是题干加Asymptote源码纯文本，没有传图片，并应与230道非图形题分层报告。
3. 基于16000部分结果决定正式输出上限、额度和批次；16000并未解决所有图形题截断，且相同样本token消耗约为4096轮的2.45倍。不要自动启动24000。
4. 冻结生成完成率、完成后正确率、端到端产出率、parser成功率和成本的统计口径。
5. 给参考答案和预测答案增加答案类型分类，逐类实现多答案、集合、区间、坐标、矩阵、单位、选择题标签和复数校验；先用合成对测试。
6. 协议稳定后才运行MATH主实验；AIME保持暂停，GSM8K只在明确补充实验时使用。
7. 实现固定revision下载脚本；最终答案链路稳定后，再开始过程步骤正确性、首错定位和错误类型设计。

## 7. 已知风险与安全边界

- **API 消耗风险**：`--all` 会运行所有待处理题；真实调用前必须先用 `--dry-run` 或精确 `--id` 检查范围。默认重试最多2次，也会增加额度消耗。
- **截断误判风险**：runner 会把HTTP成功但 `finish_reason=length` 的响应记为 `status=success`；evaluation 已增加完整性门控并输出 `unverified`，但 runner 尚无专门截断状态或自适应重试。
- **断点续跑风险**：`successful_ids()`目前会跳过所有`status=success`记录，包括`finish_reason=length`。修复前不要依赖默认resume自动补齐截断题，应使用独立实验清单和输出文件。
- **推理预算风险**：high reasoning 对简单题不一定更好，可能占满输出预算。不能简单地全局提高 `max_tokens`，否则成本和延迟会明显上升。
- **当前 baseline 参数风险**：high/4096 已实测产生46%截断；high/16000部分对照仍有4/16截断，并把相同16题token消耗提高到约2.45倍。不能直接全量放大上限。
- **图形输入风险**：50题中8道 `[asy]` 题全部截断。原始绘图代码作为纯文本进入模型，可能同时影响推理长度和题目信息可读性。
- **验证器误判风险**：`math-verify` 和当前正则启发式不是完整数学证明器。多根、集合、区间、矩阵、单位、选择题和含自然语言的答案必须保留类型化规则和人工抽检。
- **parser 启发式风险**：当回答同时给出多个等价单位或多个数学片段时，当前 parser 使用“主要加粗答案”或“最后数学片段”等规则；输出顺序异常时仍可能选错。
- **统计风险**：重复调用、失败重试和历史截断不能直接按行数计算题目正确率；应按 sample ID、inference ID 和实验配置分别统计。
- **密钥风险**：真实 `.env` 只应存在本机且已被 `.gitignore` 排除。`.env.example` 的 Key 必须保持为空。提交前仍需执行 secret audit。
- **输出数据风险**：`outputs/solver_outputs.jsonl` 保存完整模型响应、推理字段、request ID、用量和实验配置。虽然不含 API Key，仍不应未经审查公开；`outputs/` 必须继续保持忽略。
- **原始数据风险**：`data/raw/`、Hugging Face 缓存、虚拟环境和缓存文件不能提交。只提交可复现的小规模 `data/benchmark/`。
- **派生文件覆盖**：`evaluation.runner` 会重写 `outputs/answer_verification.jsonl`；solver 原始输出采用追加方式，不受影响。

## 8. 关键文件导航

- `AGENTS.md`：项目约束与记录规则。
- `PROJECT_PROGRESS.md`：简洁阶段进展和下一关键目标。
- `PROJECT_LOG.md`：追加式实施与实验日志。
- `docs/foundation/BENCHMARK.md`：benchmark组成、来源和特征。
- `docs/foundation/SOLVER.md`：solver架构、配置和输出schema。
- `docs/foundation/ANSWER_VERIFICATION.md`：验证设计、答案形态与输出格式。
- `docs/experiments/BASELINE_50_FINDINGS.md`：50题实验结果、问题状态、数据集调整和下一决策。
- `experiments/baseline_50/`：固定选择、manifest、聚合分析和问题 JSONL。
- `experiments/baseline_50/high_16000_partial_analysis.json`：已中止的16000对照聚合、样本ID与本地输出校验和。
- `solver/runner.py`：调用入口、选择、resume、重试和落盘。
- `solver/client.py`：独立 Hy3 API client 与安全持久化配置。
- `solver/parser.py`：当前答案/步骤 parser。
- `evaluation/answer_verifier.py`：数学等价判断和人工复核标记。
- `evaluation/runner.py`：连接 inference 与 benchmark 参考答案并生成验证 JSONL。
- `tests/`：solver、parser 和验证器测试。

## 9. 当前验证状态

当前本地验证目标为：19项单元测试通过，Python compileall 通过，`git diff --check` 无错误。若新会话观察到不同结果，应先检查依赖锁文件、Python版本和工作区状态，不要直接批量重跑 API。
