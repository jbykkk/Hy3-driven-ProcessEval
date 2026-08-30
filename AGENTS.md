# AGENTS.md

## 项目目标

本项目是个人参与“犀牛鸟开源实战任务”的作品。第一阶段目标是基于 Hy3 跑通数学题的分步解答流程；后续实现过程正确性评估、首个错误步骤定位和错误类型归类。

## 当前范围

- 当前不设需要全量API运行的固定主实验评测集；优先使用少量、明确目的的分层样本和受控错误样本。
- 纯文字MATH 250题（`data/benchmark/math_text.jsonl`）继续作为可复现候选池保留；其文件构成仍为官方Level 1-5每层50题，但不再要求每层50题全部调用或作为当前正式评测分母。
- 原 `math.jsonl` 的250题完整保留，其中20道含Asymptote源码；纯文字变体保留其余230题，并按同层级确定性补入20道未进入原集合的文字题。
- GSM8K 100题与AIME 50题保留在仓库中，仅作为后续候选或补充实验。
- 已整理的初始数据池仍共 400 题，不因实验范围调整而删除或改写样本；新增纯文字变体不覆盖原数据池。
- MATH保留官方Level 1-5标签；具体实验可按目的做小规模分层抽样，样本量由实验单独记录，不再固定为每层50题API调用。
- GSM8K 不额外添加难度等级，保留官方字段语义。
- AIME 作为高难度竞赛题集，不强行映射到 MATH 的等级。
- 应用输入、模型输出和评测记录统一使用 JSONL；允许在 `metadata` 中保留数据集特有字段。

## 工程约定

- 使用 `uv` 管理 Python 环境和依赖，虚拟环境位于 `.venv/`。
- Python 代码应有类型标注；数据处理应可复现，并固定随机种子。
- 原始下载数据放在 `data/raw/`，不提交 Git；可复现的小规模 benchmark 放在 `data/benchmark/` 并纳入版本管理。
- 不修改原始题目、标准答案或官方难度标签；清洗或转换必须保留来源信息。
- API Key 只能通过环境变量或未提交的本地配置注入，严禁写入源码、日志或数据文件。
- 新增命令、依赖、数据格式或目录结构后同步更新 README（创建后）和必要的项目日志。

## 数据与结果要求

- 每条样本必须拥有稳定且唯一的 `id`，并记录 `dataset`、来源 split/年份及原始标识。
- 抽样脚本必须确定性运行，记录随机种子和抽样规则，避免只提交手工挑选后的结果。
- 模型原始响应与解析结果分开保存，避免因解析覆盖原始证据。
- `PROJECT_LOG.md` 按时间正常追加决策、实施和问题记录，不重写历史。
- `PROJECT_PROGRESS.md` 仅在阶段完成、关键能力跑通、benchmark 构成变化或重要验证结论产生时更新；不记录日常命令、普通依赖调整和细小重构。
- 进展记录应简洁说明“已完成什么、当前处于哪里、下一关键目标是什么”，避免演变为流水账。

## 文档管理

- `docs/foundation/` 只存放长期稳定的工程基础说明，例如 benchmark、solver 和答案验证的设计、接口与使用方式。
- `docs/experiments/` 存放实验结果、过程中暴露的问题、解决方案和技术决策；文件名必须明确标识实验或阶段，例如 `BASELINE_50_FINDINGS.md`。
- 同一阶段、同一实验的问题报告和解决方案默认维护在一份文档中，避免按讨论轮次不断新增相互重复的文件。
- 只有进入不同阶段、发生重大技术路线调整，或两类内容具有独立维护周期时才拆分实验文档；拆分后应在文件名中清晰区分阶段或路线。
- 合并文档时删除重复叙述；已解决问题只保留必要结论、解决方式和“已解决”状态，详细历史证据放在机器可读实验记录或项目日志中。
- 移动、重命名或合并文档后，必须同步修复仓库内引用，并删除已经被替代的旧文档。
- `PROJECT_PROGRESS.md` 只保留里程碑与下一关键目标，`HANDOFF.md` 只保留新会话恢复工作所需的当前事实；两者不复制完整实验报告。
- 根目录 `TODO.md` 集中记录跨阶段的待办计划、待验证假设和已知问题，不用它替代里程碑、实验结论或实施日志。

## 按需读取与检索路由

- 默认只读取完成当前任务所需的最小信息，不在会话开始时一次性加载全部文档、完整项目日志、整个JSONL数据集或模型reasoning正文。
- 先用`rg`定位关键词、标题、样本ID或字段，再读取命中的局部范围；只有局部信息不足以完成任务时，才继续展开相邻章节或完整文件。
- 对JSONL先查看manifest、聚合统计、行数或指定样本，不直接输出整个文件。需要原始证据时按`sample_id`或`inference_id`定点查找。
- `PROJECT_LOG.md`是追加式历史记录，不是默认上下文。只有需要追溯决策时间线、历史命令或变更原因时才读取相关日期段。
- 被Git忽略的`outputs/`含完整响应和reasoning信息。只有复核具体inference、解析异常或usage时才读取指定记录，不批量加载或复制完整reasoning。
- 已从当前会话或较小摘要获得的信息不要通过读取大文件重复获取；如果摘要与源文件可能冲突，再定点核对源文件。

### 检索触发器

以下路由视为项目内的“检索hook”：任务命中某类信息时，到对应位置查找，不预加载其他类别。

| 触发条件 | 优先查找位置 | 读取边界 |
| --- | --- | --- |
| 了解当前阶段、已完成事项或下一目标 | `PROJECT_PROGRESS.md` | 默认读取全文；它必须保持简洁 |
| 新会话需要恢复整体上下文 | `HANDOFF.md` | 先读当前阶段、问题边界和下一步；需要实现细节时再跳转 |
| 查询协作规范、数据边界或文档规则 | `AGENTS.md` | 读取相关章节 |
| 查询benchmark组成、schema、来源与抽样 | `docs/foundation/BENCHMARK.md` | 先定位对应数据集章节；revision和哈希再查manifest |
| 查询solver架构、CLI、请求或输出schema | `docs/foundation/SOLVER.md` | 读取与命令或模块对应章节 |
| 查询答案解析、数学等价验证或评分输出 | `docs/foundation/ANSWER_VERIFICATION.md` | 先读取相关答案类型或评测规则 |
| 查询过程评估器、步骤解析、首错定位或过程输出schema | `docs/foundation/PROCESS_EVALUATOR.md` | 先读取证据边界和对应模块章节 |
| 查询baseline结果、截断、成本、Asymptote问题或当前技术决策 | `docs/experiments/BASELINE_50_FINDINGS.md` | 先看结论、问题状态或对应实验小节 |
| 查询Process Evaluator v1真实验证或Solver prompt v1/v2单题对照 | `docs/experiments/PROCESS_EVALUATOR_V1_SMOKE.md` | 先看结果表、适配判断和实验限制 |
| 查询Solver prompt v1/v2的MATH分层对照、过程成本或结构差异 | `docs/experiments/PROCESS_EVALUATOR_V1V2_25.md` | 先看总体结果、分Level表、配对长尾和结论边界 |
| 查询受控过程错误、答案—过程独立性、继承错误或首错定位表现 | `docs/experiments/PROCESS_EVALUATOR_ERROR_INJECTION_LEVEL4.md` | 先看构造、结果表、协议问题和实验边界 |
| 查询待办计划、待验证假设、过程评估适配或Prompt v2 | `TODO.md` | 先定位对应主题，只读取相关TODO小节 |
| 查询机器可读实验配置、汇总统计或异常样本 | `experiments/baseline_50/` | 先读`README.md`和manifest/analysis；issues与selection按ID定点读取 |
| 查询v1/v2 25题对照的选择、配置、哈希或逐样本聚合 | `experiments/process_evaluator_v1v2_25/` | 先读`README.md`和manifest/analysis；不读取被忽略的原始reasoning |
| 查询Level 4受控错误探针的预期标签、调用量或逐例对照 | `experiments/process_evaluator_error_injection_level4/` | 先读`README.md`与`analysis.json`；按需读取`cases.jsonl`，不读取内部reasoning |
| 查询新增Level 4/5 20题的选择、Solver结果或成本 | `docs/experiments/PROCESS_EVALUATOR_CANDIDATE_POOL_45.md`、`experiments/process_evaluator_v2_level45_20/` | 先看报告结论与`analysis.json`；逐题ID再查manifest，不批量读取本地reasoning |
| 查询Level 4/5 low推理20题的配置审计、成本、自然错误或high/low同题对照 | `docs/experiments/PROCESS_EVALUATOR_LOW_LEVEL45_20.md`、`experiments/process_evaluator_low_level45_20/` | 先看报告与`analysis.json`；只按异常sample读取本地可见解答，不批量读取reasoning |
| 查询后续受控错误可用的45题、来源批次或inference引用 | `experiments/process_evaluator_candidate_pool_45/` | 先读manifest；只按目标sample读取index与本地输出 |
| 查询16例分层受控错误的题目选择、注入方式、预期类型或构造校验 | `docs/experiments/PROCESS_EVALUATOR_ERROR_INJECTION_16.md`、`experiments/process_evaluator_error_injection_16/` | 先读报告与analysis；逐例标签再查cases，不批量读取本地解答或reasoning |
| 查询去除自我揭示措辞的16例v1.1构造、完整评估、人工复核或失败重试记录 | `experiments/process_evaluator_error_injection_16_v1_1/` | 先读README、human_review和evaluation_analysis；构造检查再读analysis，按case_id定点读取被忽略的聚合/原始响应，不与v1结果合并 |
| 查询新版错误分类prompt v1.2对16例重跑结果、调用成本、人工标签修订或逐例分类变化 | `experiments/process_evaluator_error_injection_16_v1_2/` | 先读README、manifest、taxonomy_review和evaluation_analysis；标签按v1.2 cases解释，原始响应按case_id定点读取，不与v1/v1.1结果合并 |
| 查询全部受控错误案例、旧Level 4是否纳入或哪些案例已经评估 | `experiments/process_evaluator_controlled_error_pool/` | 先读manifest区分案例数与源题数，再按evaluation_status读取index和来源实验 |
| 查询原始数据来源、许可或上游revision | `data/SOURCES.md`、`data/benchmark/manifest.json` | 不读取原始数据正文，除非需要核对指定样本 |
| 查询某次模型原始响应、reasoning、请求ID、token或耗时 | `outputs/*.jsonl` | 仅按sample/inference读取目标行；不得批量展示reasoning |
| 追溯历史决策、实施顺序或某日发生的工作 | `PROJECT_LOG.md` | 用日期或关键词定位后读取局部范围 |

- 如果同一任务命中多个触发器，按“当前状态/决策摘要 → 基础设计 → 机器可读证据 → 原始输出”的顺序逐层展开，在任一层信息已经足够时停止继续读取。
- 新增文档或实验材料后，如其承担新的稳定信息职责，应同步更新此路由表；临时文件和一次性分析产物不加入路由。

## 变更原则

- 优先做最小、可验证的改动。
- 下载数据集、引入大型依赖或改变 benchmark 构成前，先说明来源、许可、版本和可复现方案。
- 不提交数据集缓存、模型缓存、运行输出、密钥或虚拟环境。

## 解释说明

- 减少使用“契约”，“gold要求”等不明确的内容来进行解释和描述，尽量采用项目技术相关的语言进行解释。
- 非必要不使用SHA-256等加密算法来检验文件哈希或进行审计。
