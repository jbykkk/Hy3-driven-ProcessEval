# 项目交接说明

本文面向完全没有历史上下文的新会话。开始工作前，请先阅读根目录的 `AGENTS.md`、`PROJECT_PROGRESS.md` 和 `docs/experiments/BASELINE_50_FINDINGS.md`，再根据任务查看其他设计文档。

## 1. 项目与当前阶段

本项目是“犀牛鸟开源实战任务”的数学方向作品。开发分支为 `develop`，远程仓库为 `origin`。不要直接在 `main` 上开发。

当前进入阶段 2：Solver、最终答案验证与Process Evaluator v1已经跑通，并完成MATH Level 1-5各5题的Solver prompt v1/v2分层对照及首个Level 4受控错误探针。现有记录足以审计可见解答、逐步/全局判断与聚合结果，但仍需要独立人工标准标注才能检验Evaluator准确率。因API额度成本，已取消MATH 250题全量评测方案；后续只做少量、有明确问题和额度上限的实验。

已整理的数据池和纯文字变体均完整保留，但不代表需要全量运行：

- MATH纯文字变体：`data/benchmark/math_text.jsonl`，250题，文件构成为官方Level 1-5各50题，是默认纯文字候选池，不做250题全量API评测。
- 原MATH选择：`data/benchmark/math.jsonl`，250题，其中20题含Asymptote源码，完整保留供追溯与补充实验。
- GSM8K：100题，保留官方 test split 语义，不另加难度；仅作后续补充实验。
- AIME：50题，2024和2025各25题；暂时停止评测，仅保留为后续补充。

统一数据位于 `data/benchmark/*.jsonl`，原始下载位于被 Git 忽略的 `data/raw/`。抽样种子为 `20260824`，构建结果已做两次确定性校验。

## 2. 已完成的主要实现

### Solver

已实现以下链路：

```text
benchmark.jsonl
  -> Dataset Loader（仅 id/dataset/problem）
  -> Prompt Builder（math-solver-v1 / v2候选）
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
- 每次 inference 通过SSE流式接收并保存独立 `run_id`/`inference_id`、可见回答、内部`reasoning_content`、安全响应头、原始stream chunks、聚合响应和解析结果；正式过程评估只使用可见`response.content`。
- 正式记录区分`request_status`与`generation_status`；流式chunks同步写入独立事件JSONL，完成、正常结束但截断和异常中断不会混淆。
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
- 参考答案/预测答案的规范表达、验证器版本和错误原因

依赖为 `math-verify>=0.9.0,<1.0`，并启用官方建议的 ANTLR 4.13.2 解析支持。验证器当前优先可靠覆盖整数、分数、小数、根式、普通代数表达式和部分区间/集合。结构化答案即使自动判等，也应保留人工复核。

评测层现在先检查生成完整性：只有 `finish_reason=stop` 才进入正确性判定。截断响应中的 parser 候选会保留用于审计，但正式预测置空并标记为 `unverified`，避免把残缺推导误报为模型错答。

### Process Evaluator v1

已实现独立`process_evaluation/`链路：确定性Step Parser只切分可见`response.content`并记录结构问题；Hy3 Local Evaluator逐步输出四态判断、重要性、错误类型与错误来源；Global Evaluator检查跨步骤完整性和最终结论支持；无LLM聚合器输出保守首错、`process_correct`、答案—过程关系与复核状态。

Local/Global不读取Solver内部`reasoning_content`、参考解答或`answer_correct`。原始Evaluator响应、流事件和聚合结果分开保存。严格JSON失败不会静默修复；默认只处理一个inference、0次自动重试，已有不完整评估只有显式`--retry-incomplete`才重跑。稳定设计见`docs/foundation/PROCESS_EVALUATOR.md`。

25题分层对照中，两版50次Solver调用全部完整且答案正确，322次Evaluator调用全部`stop`并通过严格JSON；两版25/25过程正确。v2步骤减少24.5%、Evaluator总tokens减少17.7%，并把结构复核从5降至0；但Solver总tokens增加1.17%，且本轮没有错误过程，尚不能验证首错定位。详见`docs/experiments/PROCESS_EVALUATOR_V1V2_25.md`。

信息适用边界已经写入稳定设计：`reference_answer`只提供最终结论真值，`reference_solution`至多辅助标注者核对必要条件，二者都不能直接给逐步状态、错误类型或首错位置提供标准标注。正式验证还需要绑定冻结`response.content`的人工过程标注；当前阶段只做小规模受控错误，不扩展为正式人工有效性benchmark。

首个Level 4受控概念错误探针已经完成：复用同题v1/v2正确解答，把1错误地作为合数并分别搭配正确答案1518和错误答案18。4条均检测为错误过程，首错、概念错误类型、`current_step/inherited`来源和答案—过程关系全部符合预设。实验后已明确`final_answer_supported`只有在可见过程数学有效、信息充分并能推出最终答案时才为true，Global prompt升为v1.1。详见`docs/experiments/PROCESS_EVALUATOR_ERROR_INJECTION_LEVEL4.md`。

## 3. 已完成的真实 Hy3 验证

早期smoke test、跨数据集调用和答案格式验证已经证明solver与验证链路可用。50题high/4096 baseline的关键结果是27题完整、23题截断，端到端可验证答案产出率54%；全部HTTP请求均成功，因此主要瓶颈是生成预算而非API稳定性。

对截断题的high/16000对照在完成16/23题后暂停：12题恢复、4题仍截断，token消耗约为同样本4096轮的2.45倍。详细分层、成本、答案格式案例和机器可读材料索引统一见 `docs/experiments/BASELINE_50_FINDINGS.md`。

完整provider响应仍只存在于被Git忽略的`outputs/`。AIME当前暂停，GSM8K只作补充；除非用户重新授权，不要继续这些数据集的API调用。

## 4. 当前问题和处理边界

| 未决问题 | 当前边界 |
| --- | --- |
| 生成预算 | 25题分层v1/v2对照在32000下50/50完整，但成本较高；已取消250题全量方案，只允许明确额度的小样本 |
| 图形输入 | 纯文字候选池按统一规则替换20道Asymptote题；原题完整保留。Process Evaluator不读取含插图的`reference_solution` |
| 生成协议 | stream/high/32000/300秒在25题配对上无截断；批次、额度和重试仍待冻结，默认0次自动重试 |
| resume语义 | 已区分请求成功与生成完整；默认不自动重跑截断，只有显式`--retry-incomplete`才重跑 |
| 正式评测方法 | 最终答案与过程结论已独立；现有记录基本齐全，但尚需完善Solver版本、可见内容版本、原始调用引用和人工过程标注；还需确定结构化答案、temperature/seed、批次和额度上限 |

截断误评分、parser v1.2主要问题和resume状态混淆已经解决，状态见合并报告。当前明确不做分段回答和记忆系统。

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

显式重跑生成不完整的样本：

```bash
uv run python -m solver.runner --id math-test-prealgebra-0023 --retry-incomplete
```

重复同一道题并忽略所有已有记录会追加新 inference，必须显式关闭 resume：

```bash
uv run python -m solver.runner --id math-test-prealgebra-0023 --no-resume
```

重新验证所有本地 inference，不会调用 API：

```bash
uv run python -m evaluation.runner
```

由于 `outputs/` 不提交 Git，新机器或全新 clone 不会拥有早期13条或本轮50条完整 inference；同一工作区的新会话仍可读取它们。可公开复查的选择、聚合统计、异常形态和实验结论已纳入版本管理。

## 6. 下一步建议顺序

1. 在严格的`final_answer_supported`定义下，用少量样本把受控错误扩展到计算错误、非法推导、关键证据缺口、条件/case遗漏；首个概念错误探针已经通过。当前不要引入voting、ensemble或正式validity benchmark。
2. 根据25题结果确定Solver/Process Evaluator批次、额度、temperature/seed和重试策略；默认不自动重试。
3. 冻结生成完成率、完成后正确率、端到端产出率、parser成功率、过程评估完整率和成本口径。
4. 给参考答案和预测答案增加答案类型分类，逐类实现多答案、集合、区间、坐标、矩阵、单位、选择题标签和复数校验。
5. 不运行纯文字MATH 250题全量实验；后续每项API实验必须单独声明小样本选择和额度上限。AIME保持暂停，GSM8K和原图形题只在明确补充实验时使用。
6. 实现固定revision下载脚本。

## 7. 已知风险与安全边界

- **API 消耗风险**：`--all` 会运行所有待处理题；真实调用前必须先用 `--dry-run` 或精确 `--id` 检查范围。当前默认不自动重试；任何显式重试仍会增加额度消耗。
- **截断误判风险**：runner 对HTTP成功仍保留`status=success`，但已用`generation_status=complete/incomplete`区分是否正常结束；evaluation与Process Evaluator均有完整性门控。当前没有自适应重试，重跑必须显式授权。
- **断点续跑边界**：默认resume会跳过所有已有成功请求，包括`finish_reason=length`，以防相同参数自动循环调用；重跑截断必须显式使用`--retry-incomplete`并确认新参数和额度。
- **推理预算风险**：high reasoning 对简单题不一定更好，可能占满输出预算。不能简单地全局提高 `max_tokens`，否则成本和延迟会明显上升。
- **当前 baseline 参数风险**：high/4096 已实测产生46%截断；high/16000部分对照仍有4/16截断，并把相同16题token消耗提高到约2.45倍。不能直接全量放大上限。
- **图形输入风险**：历史50题baseline中的8道 `[asy]` 题全部截断。当前默认`math_text.jsonl`的模型输入`problem`已不含`[asy]`；13条`reference_solution`虽仍含示意图源码，但Process Evaluator v1不读取参考解答。
- **验证器误判风险**：`math-verify` 和当前正则启发式不是完整数学证明器。多根、集合、区间、矩阵、单位、选择题和含自然语言的答案必须保留类型化规则和人工抽检。
- **parser 启发式风险**：当回答同时给出多个等价单位或多个数学片段时，当前 parser 使用“主要加粗答案”或“最后数学片段”等规则；输出顺序异常时仍可能选错。
- **统计风险**：重复调用、失败重试和历史截断不能直接按行数计算题目正确率；应按 sample ID、inference ID 和实验配置分别统计。
- **密钥风险**：真实 `.env` 只应存在本机且已被 `.gitignore` 排除。`.env.example` 的 Key 必须保持为空。提交前仍需执行 secret audit。
- **输出数据风险**：`outputs/solver_outputs.jsonl` 保存完整模型响应、推理字段、request ID、用量和实验配置。虽然不含 API Key，仍不应未经审查公开；`outputs/` 必须继续保持忽略。
- **过程评估有效性风险**：25题对照只覆盖两版均正确且过程有效的解答；322次调用的JSON遵从率虽为100%，但没有错误过程覆盖，不能把Hy3自评结果当作已验证真值，也不能据此宣称v2首错定位优于v1。
- **原始数据风险**：`data/raw/`、Hugging Face 缓存、虚拟环境和缓存文件不能提交。只提交可复现的小规模 `data/benchmark/`。
- **派生文件覆盖**：`evaluation.runner` 会重写 `outputs/answer_verification.jsonl`；solver 原始输出采用追加方式，不受影响。

## 8. 关键文件导航

- `AGENTS.md`：项目约束与记录规则。
- `PROJECT_PROGRESS.md`：简洁阶段进展和下一关键目标。
- `PROJECT_LOG.md`：追加式实施与实验日志。
- `docs/foundation/BENCHMARK.md`：benchmark组成、来源和特征。
- `docs/foundation/SOLVER.md`：solver架构、配置和输出schema。
- `docs/foundation/ANSWER_VERIFICATION.md`：验证设计、答案形态与输出格式。
- `docs/foundation/PROCESS_EVALUATOR.md`：过程评估证据边界、步骤schema、提示词、聚合规则、输出与CLI。
- `docs/experiments/PROCESS_EVALUATOR_V1_SMOKE.md`：真实单题验证与Solver prompt v1/v2探索。
- `docs/experiments/PROCESS_EVALUATOR_V1V2_25.md`：Level 1-5各5题的v1/v2分层对照、成本、结构差异与限制。
- `docs/experiments/BASELINE_50_FINDINGS.md`：50题实验结果、问题状态、数据集调整和下一决策。
- `experiments/baseline_50/`：固定选择、manifest、聚合分析和问题 JSONL。
- `experiments/baseline_50/high_16000_partial_analysis.json`：已中止的16000对照聚合、样本ID与本地输出校验和。
- `experiments/process_evaluator_v1v2_25/`：25题选择、manifest、输出哈希和无reasoning聚合统计。
- `solver/runner.py`：调用入口、选择、resume、重试和落盘。
- `solver/client.py`：独立 Hy3 API client 与安全持久化配置。
- `solver/parser.py`：当前答案/步骤 parser。
- `evaluation/answer_verifier.py`：数学等价判断和人工复核标记。
- `evaluation/runner.py`：连接 inference 与 benchmark 参考答案并生成验证 JSONL。
- `process_evaluation/`：Step Parser、Local/Global提示词、严格schema、聚合器与运行入口。
- `tests/`：solver、parser 和验证器测试。

## 9. 当前验证状态

当前本地验证目标为：完整单元测试通过，Python compileall通过，`git diff --check`无错误；具体测试数量以最近一次`PROJECT_LOG.md`记录为准。若新会话观察到不同结果，应先检查依赖锁文件、Python版本和工作区状态，不要直接批量重跑API。
