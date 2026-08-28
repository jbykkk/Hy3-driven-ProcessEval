# 项目日志

本文件采用追加式记录，保留项目决策和重要实施过程。

## 2026-08-24

- 确定任务领域为数学，第一阶段优先完成基于 Hy3 的数学题分步解答应用。
- 初始 benchmark 计划为 400 题：GSM8K 100 题、MATH 250 题、AIME 50 题。
- MATH 沿用官方五级难度，每级抽取 50 题；GSM8K 不新增难度标签；AIME 作为高难竞赛题集处理。
- 确定应用输入输出和后续评测记录统一采用 JSONL，同时保留数据集特有元数据。
- 使用 `uv` 创建 Python 3.10.20 虚拟环境 `.venv`。
- 初始化 `main` 分支 Git 仓库，并建立项目协作、进展和日志文件。
- 创建并切换到 `develop` 开发分支；后续开发变更不直接提交到 `main`。
- 确认 AIME 从 2024、2025 两年各抽取 25 题。
- 通过 Hugging Face Hub 下载 GSM8K、MATH、AIME 2024 和 AIME 2025 原始数据，并记录上游 revision；尚未进行抽样或格式转换。
- 发现 MATH 官方 README 当前链接的数据副本丢失原始 train/test split；额外下载并选定保留原始 split 的 `EleutherAI/hendrycks_math` 镜像作为后续抽样来源。
- 更新协作规范：进展文件只记录阶段性里程碑和关键结论，日常实施过程继续追加到项目日志。
- 增加 `pyproject.toml` 和 `uv.lock`，使用 `pyarrow` 读取原始 Parquet 数据。
- 实现确定性 benchmark 构建脚本，固定种子为 `20260824`，按稳定样本 ID 的 SHA-256 排序抽样。
- 生成 `data/benchmark/`：GSM8K 100题、MATH五个 Level 各50题、AIME 2024/2025各25题，并提供合并后的400题 JSONL 与 manifest。
- 连续两次生成所得文件 SHA-256 完全一致；数量、唯一 ID、必填字段及分层检查均通过。
- 新增 benchmark 数据说明文档，记录实际组成、MATH 学科交叉分布、各数据集答案与参考过程特征，以及对后续答案校验和过程评估的影响。
- 确定 solver 直接通过腾讯云 TokenHub 的 OpenAI-compatible API 调用 Hy3，不再考虑 CodeBuddy 调用通道。
- 实现 Dataset Loader、Prompt Builder、独立 Hy3 Client、Response Parser 和可恢复 Runner；模型输入类型只允许 `id`、`dataset`、`problem`，不会携带标准答案或参考信息。
- solver 输出逐条记录完整请求配置（不含密钥）、可见解答、`reasoning_content`、原始 API 响应、usage、请求标识、耗时、重试错误和解析结果。
- 增加单题安全默认值、显式 `--all`、断点续跑、dry-run、环境变量样例和5项自动化测试；真实 Hy3 调用等待本机配置 `HY3_API_KEY`。
- 增加被 Git 忽略的本地 `.env` 配置方式；solver 自动加载该文件，且显式 shell 环境变量优先。
- 完成首次真实 Hy3 API 调用：`gsm8k-test-0008` 一次请求成功，HTTP 200，耗时约23.46秒，总计2027 tokens，其中推理 tokens 为1423。
- Hy3 输出7个连续编号步骤并得到45英里，与 benchmark 标准答案一致；完整原始响应、可见解答、思考字段、usage和时间信息已写入本地输出。
- 首次解析将自然语言答案整句作为候选，暴露 Markdown `**Answer:**` 格式兼容问题；更新 parser 至 `solution-parser-v1.1` 后，在不重新调用 API 的情况下从原始响应正确提取答案45，6项测试全部通过。
- 增加独立最终答案验证层，采用 `math-verify 0.9.x` 与 ANTLR 4.13.2 将参考答案和预测解析为数学表达式；验证结果按 inference 单独写入 JSONL，不覆盖 solver 原始证据。
- 审计当前 benchmark 的参考答案形态：GSM8K 100题和 AIME 50题均为整数；MATH 包含167个整数答案、37个分数/有理式、12个根式，以及元组、区间、集合、矩阵、单位、选择标签等结构化类型。
- 完成跨数据集小规模验证：沿用已有 GSM8K 结果，新增两次 MATH 分数题、一次 MATH 根式题、一次 MATH 混合数题和一次 AIME 2024 题调用；五次新增调用均一次成功，共使用8918 tokens。
- 6次 inference 的最终答案均验证正确。根式预测 `5 + 6\sqrt{2}` 对参考答案 `5+6\sqrt{2}`，混合数预测 `8\frac{4}{7}` 对参考答案 `8\frac47`；两组字符串不同但数学等价，均被标记为 `format_mismatch_but_equivalent`。结构化多答案类型暂列为人工复核范围。
- 开展第二轮 GSM8K/MATH 多格式实验，覆盖货币与千位分隔符、等价单位、分数/小数、含 π 表达式、区间和无序多根；6道目标题最终均正确，区间与多根虽自动判等仍保留人工复核标记。
- 将 parser 升级至 `solution-parser-v1.2`，修复无 `Answer:` 标签结论、主要答案后附等价单位、以及 `\(...\)` 中多个等价表达的提取；从已有原始响应重新解析后，将三条漏提取/误提取记录恢复为正确，无需再次调用 API。
- 多根题在 high reasoning 下耗尽4096 completion tokens，返回 `finish_reason=length` 且无可见答案；改用 low reasoning 后以1988 tokens 完成，根顺序不同但集合等价。保留首次截断记录为 `unverified`，后续需将截断和推理预算监控纳入批量 runner。

## 2026-08-25

- 新增 `HANDOFF.md`，面向零上下文的新会话汇总当前阶段、已完成实现、真实验证结果、运行步骤、下一优先级以及 API、密钥、截断、验证误判和本地输出等风险。
- 核对并更新 `PROJECT_PROGRESS.md`：已反映 GSM8K/MATH 多格式答案实验，当前下一目标仍是结构化答案校验、截断重试策略、扩大分层验证和固定 revision 下载脚本。
- 使用固定种子 `20260825` 生成50题分层 baseline：GSM8K 13题、MATH 31题（Level 1为7题，其余各6题）、AIME 2024/2025各3题；选择文件校验和为 `a516f864b9eabb6d44bcd7d11d896aa17bb8cb328f5921e32f20e831809b1cf5`。
- 统一以 Hy3、thinking enabled、high reasoning、`max_tokens=4096` 完成50次调用；全部一次请求成功，无API错误或重试，总计135,966 tokens、串行 inference 延迟约29.2分钟。
- 50题中27题正常结束、23题 `finish_reason=length`，其中22题可见内容为空；GSM8K/MATH/AIME截断率分别为15.4%、48.4%、100%。截断请求消耗总 token 的72.1%。
- 发现8道含 `[asy]` Asymptote 绘图代码的题目全部截断，非 Asymptote 题为15/42截断；将图形题输入形式列为需单独控制的混杂因素。
- parser 升级至 `solution-parser-v1.3`，从最后编号步骤的明确 final/total/maximum 等上下文提取答案，并优先保留显式 Answer 标签；离线重评后27条完整回答全部验证正确，23条截断保留为 `unverified`，18项测试通过。
- 新增 baseline 聚合分析、31条机器可读问题记录和实验报告。腾讯官方当前说明思考与回答共享输出额度，Hy3出现空响应/截断时建议 `max_tokens>=16000`；下一步保持 high reasoning 做小规模16000上限对照，不直接批量重跑。
- 对23条high/4096截断题发起high/16000单变量重跑；用户在完成16题后暂停，保存结果为12条正常结束、4条仍截断、7条无本轮记录，未运行到AIME，也未启动24000测试。
- high/16000已完成16题共消耗167,169 tokens，约为同16题4096轮68,100 tokens的2.45倍，平均单题延迟约127.8秒；7道Asymptote题中4道仍截断，9道非Asymptote题全部恢复。
- 修复答案评测的生成完整性门控：只有 `finish_reason=stop` 才参与正确性判断，截断正文中的候选答案仅审计并标记为 `unverified`，消除残缺字符串造成的假错答。
- 调整实验范围：MATH 250题（Level 1-5各50题）成为当前主评测集；GSM8K与AIME数据继续保留但仅作后续补充，AIME评测暂时停止。
- 将solver默认输入切换为 `data/benchmark/math.jsonl`；补充数据集必须显式指定 `--input`，避免后续误把400题合并文件或AIME纳入主实验。
- 新增当前问题与决策总览，统一记录截断、token成本、Asymptote输入、评分门控、parser/验证器限制、resume语义和非确定性，并同步刷新项目进展与零上下文交接文档。
- 重组`docs/`：工程说明统一移至`docs/foundation/`，实验问题与决策移至`docs/experiments/`；将两份重复的baseline/问题报告合并为`BASELINE_50_FINDINGS.md`并修复引用，同时把文档分类、合并和命名规则加入`AGENTS.md`。
- 在`AGENTS.md`增加按需读取规范与检索触发器：默认使用最小上下文，按任务路由到进展、交接、基础设计、实验结论、机器记录或原始输出，并限制整批读取日志、JSONL和reasoning正文。

## 2026-08-26

- 对4道不含Asymptote的MATH Level 4/5题执行high/16000输出长度探针，覆盖几何、数论、计数与概率和中等代数；关闭自动重试并写入独立本地输出。
- 3题以`stop`完成，completion tokens分别为1005、3979和2924，均离线验证正确；另1道Level 5中等代数题耗尽16000 completion tokens且全部为reasoning tokens，没有产生可见答案，标记为`unverified`。
- 四题合计消耗23,908 completion tokens，其中22,637为reasoning tokens，串行延迟约333.3秒。该探针说明提高上限不会按上限预扣token，但会放大少数失控推理的实际成本和尾部延迟；16000仍不能保证完成。
- 将上述16000截断的Level 5中等代数题和一道人含Asymptote源码的Level 5几何题改用high/32000继续探测。首次图形题调用受原300秒客户端timeout限制失败，随后将timeout放宽至1800秒并保持`max_retries=0`；中等代数题在旧批次刚开始后即人工中止，再以新timeout执行。
- 1800秒timeout下两题均以`stop`完成并验证正确：图形题使用20,452 completion tokens（19,670 reasoning），耗时272.6秒；中等代数题使用14,374 completion tokens（13,586 reasoning），耗时193.6秒。结果说明32000能够覆盖本次两个长尾样本，但非流式timeout必须同步放宽；temperature 0.9下同题推理长度也存在明显波动。
- 新增`docs/experiments/PROCESS_EVALUATION_PROMPT_TODO.md`，明确正式过程评估只使用可见`response.content`，内部`reasoning_content`仅作本地诊断；记录`math-solver-v2`的原子步骤、依据与依赖标注、兼容parser、错误样本和v1/v2受控对照计划，当前不实现也不启动全量调用。
- 按用户要求将专用过程评估TODO迁移为根目录通用`TODO.md`，集中记录跨阶段计划、待验证假设和已知问题；删除原专用文档并同步更新`AGENTS.md`检索路由。
- 将Hy3客户端由非流式完整响应切换为SSE流式接收，启用最终usage chunk，分别聚合`reasoning_content`与可见`content`，同时保留原始stream chunks；新增流聚合和不完整流测试。
- 使用`math-test-algebra-0144`完成一次真实流式smoke test：接收717个chunks，`finish_reason=stop`，使用2085 completion tokens（1783 reasoning），parser提取答案64且离线验证正确；完整结果保存在本地忽略的`outputs/`。
- 将solver记录schema扩展为1.1，显式区分`request_status`与`generation_status`；默认resume继续跳过已有成功请求以防相同参数循环调用，新增`--retry-incomplete`作为截断重跑的显式授权，并将默认自动重试数改为0。
- 将流式chunks增量写入独立事件JSONL，使用`stream_started`、`stream_completed`、`stream_incomplete`和`stream_interrupted`区分完整结束、达到上限和异常中断；正式solver记录仍只在聚合完成后落盘。
- 将当前生成协议候选设为SSE stream、high reasoning、`max_tokens=32000`、300秒网络读取timeout；批次、额度、temperature/seed和重试策略仍待分层实验冻结。
- 使用上述候选协议对新样本`math-test-intermediate_algebra-0878`执行一次Level 5非图形测试：总耗时503.2秒但因持续流式传输未触发300秒读取超时，9650个chunks完整结束，使用24,744 completion tokens（23,987 reasoning），答案17且离线验证正确。
- 基于已下载的`EleutherAI/hendrycks_math`固定revision新增纯文字主实验变体`data/benchmark/math_text.jsonl`：完整保留原230道非图形题，按Level分别排除5/6/1/4/4道Asymptote题，并从未进入原选择的同Level纯文字test候选中确定性补齐20题。
- 新增`math_text_manifest.json`记录筛选规则、原`math.jsonl`哈希、逐层排除与替换ID和输出哈希；两次完整重建均得到250个唯一ID、Level 1-5各50题、0道`[asy]`及相同SHA-256 `007b163e212272059562bff67e314ad19a6506d44c5799677b94cd9dafea40da`。
- 原`math.jsonl`与400题`benchmark.jsonl`未删除或改写，哈希仍分别为`6ddb04a0360ff93e467ac05467867a59ee612a5924156e27dd91fa5cbdc8cc6f`和`139cad7cc58b478338acba333e308e9bf250890fff67ad8c093b47600a369e39`；solver与evaluation默认输入切换到纯文字变体。
- 明确纯文字变体的字段边界：250条模型输入`problem`均不含`[asy]`；13条不进入solver prompt的`reference_solution`仍含解释性Asymptote插图，已写入manifest并列为后续过程评估器需要单独处理的问题。

## 2026-08-28

- 实现独立Hy3 Process Evaluator v1：确定性Step Parser保留完整`response.content`与步骤原文，并显式报告无步骤、编号不连续、重复编号、空步骤和最终答案缺失等结构问题。
- 新增`math-process-evaluator-v1`与`math-global-evaluator-v1`，Local按`valid/invalid/insufficient/uncertain`、`low/medium/high`重要性、固定错误分类和`none/current_step/inherited/uncertain`错误来源返回严格JSON；Global检查跨步骤完整性与最终结论支持度。
- 新增无LLM聚合器，独立读取已有答案验证元数据，支持`answer_correct=true`但`process_correct=false`；Local首错与Global override同时保留，冲突或高影响不确定时进入人工复核。
- Evaluator原始API响应、流事件和最终过程记录分别写入三个被Git忽略的JSONL；原始响应先于schema解析落盘，解析失败不静默修复，默认不自动重试且不自动反复重跑不完整评估。
- 增加用户提供的`math-solver-v2`过程友好提示词和显式`--prompt-version`选择；v1继续作为默认复现基线，待同题单次探索和后续小规模受控实验后再决定是否切换。
- 对既有`math-test-algebra-0144` v1解答完成5次Local和1次Global真实评估，6次调用均`stop`且通过严格JSON；5步均为`valid`，Global为`valid/complete/supported`，聚合为`correct_answer_valid_process`，Evaluator共使用4,790 completion tokens。
- 使用相同Solver参数仅替换prompt生成同题v2解答，最终答案仍正确；v2为3步且显式`Final Answer:`，再完成3次Local和1次Global评估，4次调用均通过，Evaluator completion tokens为3,076。
- 单题v2相对v1减少33.3%的Evaluator调用、约35.8%的Evaluator completion tokens和约37.5%的累计调用延迟，但把两个关键推断合并进同一步，错误定位粒度可能变粗；由于本题无错误且每版只运行一次，结论仅作为可行性探索，未将v2升为默认。
- 最终本地回归为38项单元测试全部通过，覆盖严格JSON失败保留原始响应、历史Solver schema兼容、不完整评估显式重试、继承错误不重复定位和答案正确但过程错误等边界；Python compileall与`git diff --check`同时通过。
- 使用固定种子`20260828`从`math_text.jsonl`确定性选择Level 1-5各5题，排除先前单题probe，共25题；选择文件SHA-256为`7b980f136d0e6d1d7c6af56ad3fadedb52a6d37489697a82d87692af6c10fb96`，覆盖7个学科。
- 以stream/high/32000/300秒、temperature 0.9、0次重试对25题分别运行`math-solver-v1`和v2，共50次Solver调用全部一次完成、无截断和parser warning；两版最终答案均25/25正确。
- v1生成155步、v2生成117步，v2减少24.5%；v1有5条`final_answer_missing`结构告警，v2为0。v2可见字符仅减少2.7%，表明单步平均更密集，潜在首错粒度需要另行验证。
- 对50条解答执行322次Process Evaluator调用：v1为180次、v2为142次，全部`stop`且严格JSON有效；两版所有Local步骤和Global结果均为`valid`，25/25过程正确。v1的5条结构告警触发复核，v2复核数为0。
- v2相对v1减少21.1% Evaluator调用、14.1% Evaluator completion tokens和17.7% Evaluator总tokens；但Solver completion仅减少3.45%，更长prompt使Solver总tokens增加1.17%。端到端Solver+Evaluator总tokens从445,964降至390,696，减少约12.4%。
- 25个配对中v2步骤更少19题，但Solver completion更少仅8题、更多17题；Level 1/2 v2 Solver成本明显上升，且存在24,490-token反例。结论是v2主要降低过程评估成本，并不稳定降低Solver推理成本。
- 本轮所有解答均正确且过程有效，不能检验`invalid/insufficient`、错误来源或首错定位。下一关键实验改为小规模受控错误过程，不继续用正确样本数量替代Evaluator有效性验证。
- 新增25题选择与聚合脚本测试后，最终完整回归为40项单元测试全部通过，Python compileall与`git diff --check`通过；selection、manifest和analysis连续重建哈希一致。
- 整理v2 Solver与Process Evaluator的信息契约：v2可见解答提供连续数学阶段、关键依据、条件/case和显式最终答案；Evaluator保留确定性步骤、逐步四态判断、错误类型/来源、全局完整性与支持度、首错和聚合关系，已足以审计运行链路。
- 明确有效性验证边界：官方`reference_answer`只能验证最终结论，`reference_solution`只可辅助标注且不能作为唯一过程gold；当前25题全为正确过程，尚不能证明错误判定或首错定位能力。
- 将后续计划拆为来源关联增强、独立过程gold协议、小规模受控错误集和之后的自然错误正式有效性集；当前阶段仍不实现人工validity benchmark、multi-agent voting或ensemble。
- 复用`math-test-prealgebra-0485`既有v1/v2正确解答构造首个受控错误探针：把1错误地视为合数并一致推导18，每版分别搭配正确答案1518和错误答案18，共4条；未重新调用Solver。
- 28次有效Process Evaluator调用均一次完整。4条全部检测为错误过程，首错位置、`concept_or_theorem_error`、`current_step/inherited`来源及答案—过程关系均符合预设；两个正确答案变体均得到`correct_answer_invalid_process`。
- 错误答案18与错误推导局部一致时，v1/v2 Global的`final_answer_supported`分别为false/true；将字段语义冻结列为下一待办。本轮有效调用共使用29,921 completion tokens、54,770 total tokens，累计调用延迟310.1秒。
- 统一`final_answer_supported`定义：只有可见推理在数学上有效、信息充分且能推出最终答案时才为true；与错误链条局部一致不算支持。Global prompt升级为`math-global-evaluator-v1.1`，严格schema增加状态一致性检查，历史响应不回写。
- 因API额度成本，取消MATH纯文字250题、Level 1-5每层50题的全量评测方案。所有数据文件、官方Level标签和既有实验继续保留；后续只运行有明确问题、选择规则、样本数和额度上限的小规模实验。
