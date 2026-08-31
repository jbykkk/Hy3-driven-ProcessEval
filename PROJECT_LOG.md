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

## 2026-08-29

- 明确后续Process Evaluator开发不采用固定100题或MATH 250题全量API方案；历史实验、benchmark和本地输出全部保留，受控错误注入只基于已有Solver解答开展。
- 使用固定种子`20260829`从纯文字MATH中选择与旧25题不重合的Level 4/5各10题；每层优先覆盖所有可用官方学科，再均衡补足至10题。Level 4覆盖7个学科，Level 5覆盖该层实际存在的6个学科。
- 以Hy3、`math-solver-v2`、stream/high/32000/300秒、temperature 0.9和0次自动重试运行新增20题。受限网络预检产生20条不消耗模型tokens的连接错误；联网后20次调用全部一次`stop`，parser均无警告。
- 新增20题最终答案20/20正确，3题为格式不同但数学等价，其中1个三元坐标答案保留人工复核建议；共使用183,742 total tokens，其中166,318为reasoning tokens，占90.5%。
- 将旧25题的v2 inference与新增20题整理为45题过程评估候选池：Level 1-3各5题、Level 4-5各15题，45/45生成完整且答案正确。统一索引保存逐题输出路径和inference ID，不复制本地可见解答或内部reasoning。
- 从45题池选择16道不同源题构建新受控错误集：Level 1-3各2题，Level 4-5各5题，其中Level 4/5各有1个额外正确答案但错误过程案例；未修改任何原始Solver输出。
- 受控集覆盖除`other`外的8种固定错误类型：概念或定理错误3例、非法推导3例、条件遗漏3例、计算错误2例、case遗漏2例，题意误解、关键依据不足和答案格式错误各1例。
- 合成记录保留v2可见Step边界并清空内部reasoning，明确标识为受控输入而非provider响应。Solver parser与Process Step Parser均16/16无警告或结构问题，所有预设首错Step存在。
- 离线答案验证与预期16/16一致：13例答案错误，3例答案正确但过程无效或依据不足；Level 4/5要求的正确答案错误过程案例分别为不等号方向错误后输出28、错误指数枚举得到168后输出42。当前尚未调用Process Evaluator。
- 将此前`math-test-prealgebra-0485`的4个Level 4已评估变体与新16例建立统一受控错误池索引：共20个案例、17道不同源题；旧4例标记为`evaluated`并引用原analysis，新16例标记为`not_run`，原实验与输出均不移动或覆盖。
- 对新16例运行Process Evaluator：79次Local与16次Global共95次调用，全部请求成功、生成完整、严格JSON有效且无自动重试；共使用213,477 total tokens，其中109,531 reasoning tokens，累计调用延迟约1,095.1秒。
- 首轮结果为过程错误检出16/16、首错Step 14/16、错误类型11/16、Local状态13/15、Local类型10/15、Local来源13/15、Global状态16/16、`process_complete`9/16、`final_answer_supported`16/16、答案—过程关系16/16；3例进入复核。
- 三个正确答案但无效或不充分过程案例均得到`correct_answer_invalid_process`与`final_answer_supported=false`。首轮同时暴露数据构造问题：多条注入文本主动使用错误提示措辞，两个案例被Local解释为正确指出错误；负半径案例还出现Step 7虚假计算错误与Global Step 9冲突。结果保留为首轮受控行为探针，不宣称自然错误准确率。
## 2026-08-29：构造去提示化受控错误集 v1.1（未运行评估器）

- 保留已评估v1不变，另建16例v1.1，将错误作为自然解题陈述、计算或选择写入过程，删除直接暴露错误的措辞与元叙述。
- 对全部评估器可见`response.content`完成人工语义复核和本地模式扫描，自我揭示命中0条；步骤解析与结构异常均为0。
- 离线答案核验与预期16/16一致：13条错误答案、3条正确答案但过程错误。未调用Process Evaluator，v1.1保持`not_run`。

## 2026-08-29：完成去提示化 v1.1 Process Evaluator 评估

- 用户确认后仅对`process_evaluator_error_injection_16_v1_1`运行评估，使用79次Local与16次Global，共95次有效调用；含自我揭示措辞的v1输出、原始响应和聚合结果未覆盖或混入。
- 初始沙箱网络失败产生16次无响应连接错误，随后使用`--retry-incomplete`完成全部95次有效调用；失败尝试保留在v1.1原始响应与流事件中，不计入成功评估分母。
- v1.1结果：过程错误检出15/16、首错Step15/16、错误类型9/16、Local状态14/15、Local类型7/15、Local来源14/15、Global状态16/16、答案支持度16/16、答案—过程关系15/16，3条需要复核。
- 成功调用使用214,530 total tokens（110,592 reasoning），累计有效调用延迟约1,056.7秒。错误类型偏差属于自然错误文本下的邻近类别边界，后续应单独复核，不与v1结果合并。

## 2026-08-30：完成 v1.1 三条人工复核与指标修订

- 对v1.1的3条`needs_review`逐一复核Solver可见过程、Local/Global判断与聚合结果，并新增结构化裁决`experiments/process_evaluator_error_injection_16_v1_1/human_review.json`；未重新调用API，也未修改任何模型输出。
- 选择题案例的数学推理正确且完整，但最终输出`34`而不是choice `C`，保留为真实`answer_extraction_or_format_error`；Evaluator实质判断正确，复核主要暴露当前schema不能把`final_answer`表示为错误位置。
- 复数遗漏分支案例的Step 4仅合法分析`y=0`分支，首个致命错误实际在Step 5宣称唯一解时发生。v1.1人工gold由Step 4修正为Step 5，`process_complete`由true修正为false；旧v1的Step 4原文明示遗漏分支，因此旧标签和历史结果不变。
- 负半径案例的Step 7两式数学等价，Local的计算错误判断属于假阳性；Global正确恢复Step 9，但与Local冲突且类型仍偏离人工`condition_omission`标签，聚合器保守进入复核。
- 按修正后gold重算v1.1：过程错误检出15/16、首错14/16、错误类型9/16、Local状态15/15、Local重要性15/15、Local类型8/15、Local来源14/15、Global状态16/16、`process_complete` 13/16、答案支持度16/16、答案—过程关系15/16。复核前首错15/16不再作为最终结果。
- 本地重建构造与派生分析后，自我揭示命中仍为0条、步骤结构异常0条、答案预期匹配16/16；旧v1与v1.1继续分开保存和统计。

## 2026-08-30：更新错误类型分类边界

- 将共享错误类型提示词升级为“先定位最早主要错误事件，再分类”：明确排除继承错误与下游症状，只允许依据可见文本判断，诊断问题不作为搜索错误的绝对优先级列表。
- 为9个固定类型补充定义与排他边界，重点区分任务表示错误与条件未执行、分支遗漏与可接受性条件遗漏、错误一般规则与具体非法推导、非法推导与合法运算的执行失误，以及关键依据不足与可识别的具体遗漏。
- 明确仅分析一个分支本身不构成`case_omission`；非法变换先导致解丢失时，首因归为`invalid_derivation`；只有前述数学过程正确、完整且充分时才使用`answer_extraction_or_format_error`。
- Local prompt版本升为`math-process-evaluator-v1.1`，Global prompt版本升为`math-global-evaluator-v1.2`。本次未修改schema、Local/Global调用流程、首错聚合器或历史实验结果，也未调用API。

## 2026-08-30：新版错误分类 prompt v1.2 重跑

- 在实验前审计确认`process_evaluation/`中仅分类prompt及其版本号变化；`schema.py`、`step_parser.py`、`aggregator.py`、`runner.py`和调用流程未修改。旧v1/v1.1输出未覆盖。
- 使用新版分类定义对同一16例、同一人工gold和同一Solver可见解答运行Process Evaluator。首轮16次连接失败不含模型响应；14道目标首轮完整，2道目标显式重试后完整，共106次成功响应（105 Local、17 Global），原始响应122条。
- v1.2结果：过程错误检出16/16、首错16/16、错误类型11/16、Local状态15/15、Local重要性15/15、Local类型10/15、Local来源15/15、Global状态16/16、`process_complete` 13/16、答案支持度16/16、过程正确16/16、答案—过程关系16/16、`needs_review` 1/16。
- 相比人工复核后的v1.1，错误检出由15/16提升至16/16，首错由14/16提升至16/16，错误类型由9/16提升至11/16，Local来源由14/15提升至15/15，`needs_review`由3/16降至1/16。题意误解、候选根遗漏、排除条件和复数首错等边界得到改善。
- 仍有5例类型偏差：`invalid_derivation`与`calculation_error`/`concept_or_theorem_error`之间，以及末端条件遗漏与`answer_extraction_or_format_error`之间仍有混淆。唯一复核案例仍为选择题格式，主要是`final_answer`无法由当前Step schema表示，不属于数学过程判断失败。
- 汇总记录见`experiments/process_evaluator_error_injection_16_v1_2/evaluation_analysis.json`，运行说明和独立manifest见同目录；v1/v1.1/v1.2三轮结果严格分开。
- 本轮使用353,599 total tokens（134,182 reasoning tokens），累计调用延迟约1,387.4秒；指标均相对冻结的v1.1人工gold，没有新增人工标签修订。

## 2026-08-30：v1.2分类标签人工复核与指标修正

- 发现v1.2初始11/16是新版Prompt预测直接对照v1.1旧版分类标签的过渡统计；由于预测与人工标签必须使用同一版定义，该数字不再作为v1.2最终分类指标。原API响应保持不变，本次仅离线重建标签与汇总。
- 按新版“先定位首因，再依据定义和排他边界分类”的规则复核全部16例：13条标签保持不变，3条修订。德摩根实例由`concept_or_theorem_error`改为`invalid_derivation`；错误幂和恒等式及错误奇素数指数一般规则由`invalid_derivation`改为`concept_or_theorem_error`。
- 修正奇素数指数案例中已与去提示化可见解答不一致的旧注入说明；不修改题目、Solver可见解答、Evaluator输出或v1/v1.1实验记录。
- 复核后的v1.2最终结果为错误类型14/16、Local类型13/15；过程错误16/16、首错16/16及其余指标不变。标签修订并非迁就预测，仍保留2条Evaluator分类错误：不等式变号的`invalid_derivation`被判为`calculation_error`，负半径的`condition_omission`被判为`answer_extraction_or_format_error`。
- 唯一`needs_review`仍是选择题输出格式案例：Evaluator识别了`final_answer`错误，但当前编号Step schema无法表示该特殊位置。完整复核见`experiments/process_evaluator_error_injection_16_v1_2/taxonomy_review.json`，最终统计见同目录`evaluation_analysis.json`。

## 2026-08-30：Level 4/5 low自然错误探针

- 核对确认新增Level 4/5共20题此前只完成high Solver与最终答案验证，20/20正确；自然可见解答未作为一批运行Process Evaluator，已完成的是另行构造的受控错误评估。
- 从原确定性选择中每层按顺序取前5题，共10题；Solver与Process Evaluator只把`reasoning_effort`从high改为low，其余prompt、temperature、token上限、stream、timeout和0次自动重试保持不变，输出使用独立路径。
- 10次Solver调用全部`stop`、parser无警告，最终答案10/10正确；共使用31,506 total tokens和22,865 reasoning tokens。对应10题high Solver为108,288 total tokens和99,521 reasoning tokens，low分别减少70.9%和约77.0%。
- Process Evaluator对61步执行Local、对10题执行Global，共71次调用；全部请求成功、生成完整且严格JSON有效，使用194,262 total tokens和38,713 reasoning tokens。
- Evaluator预测9/10过程有效；Level 5样本`math-test-precalculus-0488`得到正确答案`6/23`，但Step 7把常数项写成`+1`后无有效过渡地切换到含`-36`的正确二次方程。Local与Global均定位Step 7并分类为`calculation_error`，人工定点核对确认是真实可见错误，聚合为`correct_answer_invalid_process`。
- 其余9条valid预测尚未逐步人工标注，本轮只作为自然错误探针，不报告Evaluator准确率或误报率；下一步先人工抽检，再决定是否运行剩余10题。
- 实验材料JSON校验、`git diff --check`、Python compileall及51项单元测试全部通过；密钥模式扫描无命中。

## 2026-08-30：完成剩余10题并汇总low 20题

- 从原Level 4/5各10题固定选择中计算首批补集，得到剩余Level 4与Level 5各5题；与首批合并后覆盖20/20且无重复。第二批使用独立`remaining10`输出路径，未覆盖首批或high结果。
- 第二批10次Solver请求逐条审计均为`reasoning_effort=low`，全部`stop`、parser无警告、最终答案10/10正确；其中三元坐标答案只是LaTeX空格格式不同，数学等价但保留结构化答案人工复核建议。
- 第二批55次Local与10次Global共65次Evaluator调用全部为low、请求成功、生成完整并通过严格JSON，10/10预测过程有效且无需复核。
- 合并审计确认20条Solver请求和136次Evaluator调用的reasoning强度唯一值均为low，非low记录数为0。整体20/20答案正确，Evaluator预测19/20过程有效；唯一错误仍是已人工确认的`math-test-precalculus-0488` Step 7符号错误。
- low Solver 20题共60,706 total tokens、43,550 reasoning tokens；对应high为183,742与166,318，分别减少67.0%和73.8%。Level 4 total tokens减少63.1%，Level 5减少69.8%。low可见步骤116，高于high的110，因此成本下降主要来自内部reasoning而非减少步骤。
- low Evaluator共使用365,789 total tokens，其中69,610 reasoning tokens；由于没有high Evaluator同题批量结果，不报告Evaluator high/low成本降幅。完整实验已收敛到`PROCESS_EVALUATOR_LOW_LEVEL45_20.md`与`experiments/process_evaluator_low_level45_20/`，不保留重复的10题临时报告。
- 最终机器可读JSON、仓库引用、密钥模式和`git diff --check`均通过，当前完整51项单元测试再次全部通过。

## 2026-08-31：全实验与结果报告准备度整理

- 按任务交付要求盘点稳定设计、历史baseline、Prompt v1/v2对照、45题候选池、受控错误三轮评估和low自然错误实验；确认核心工程与阶段实验已经比较完整，可以进入统一口径与总报告阶段。
- 新增`docs/experiments/PROJECT_RESULTS_READINESS.md`，将实验按用途分层，明确哪些数字可进入主结论、哪些只能作为历史配置或行为探针，并提出统一的生成、答案、过程、有效性、复核和成本指标定义。
- 主要结论建议以v1.2受控16例与low Level 4/5各10题为核心；baseline、单题smoke、旧v1/v1.1和high候选池作为问题发现、路线演进或对照证据，不混合成一个总准确率。
- 识别最终交付缺口：19条自然valid预测缺少系统人工抽检、`final_answer`错误位置未实现、缺公开逐样本结果索引、统一结果报告、demo、开源许可证和固定revision下载脚本；当前难度证据不足以声明明确能力下降临界点。
- 新增根目录`README.md`，整理项目目标、核心链路、主要结果、数据边界、快速开始和文档导航；TODO、进展、交接与检索路由同步更新。
- 整理后完整51项单元测试、Python compileall、文档链接目标检查和`git diff --check`均通过。

## 2026-08-31：明确45题覆盖关系与low扩展方案

- 核对45题候选池由旧25题v2和新增Level 4/5共20题组成，Level 1-5分布为5/5/5/15/15；45条high Solver自然解答均完整且答案正确。
- 明确high自然过程评估当前只覆盖旧25题；新增20题只完成high Solver与答案验证。受控16例从45道源题派生并独立人工改写，不属于45条high自然解答，也不覆盖原输出。
- low自然实验当前只覆盖新增20题，20条Solver与136次Evaluator调用均为low。计划复用旧25题v2选择补充low运行，合并为与high同题、同层级分布的45题自然实验。
- 将low 45的用途限定为同题Solver准确率/成本、分层能力探索和自然过程样本扩充；最终答案正确不能代替过程人工真值，正式误报率和漏报率仍需分层人工复核。
- 明确Solver推理强度和Evaluator推理强度是两条分析轴：同时改变两者只能比较整条流水线；Evaluator强度比较必须冻结同一可见解答，优先在受控16例和人工复核自然样本上做小规模对照。
- 记录现有Evaluator配置差异：旧25题high使用Local/Global v1，low 20使用Local v1.1与Global v1.2，因此两批结果不能解释为只改变推理强度；正式Evaluator high/low对照还需固定prompt版本。

## 2026-08-31：完成low自然45题与新版Evaluator强度对照

- 对旧25题v2固定选择运行low Solver：25/25完整、无parser warning、答案25/25正确，使用52,888 total tokens和35,643 reasoning tokens；与既有low 20题合并后形成Level 1-5为5/5/5/15/15的low自然45题。
- low自然45题Solver共113,594 total tokens与79,193 reasoning tokens，同题high分别为311,089与275,718，减少63.5%与71.3%；两种强度均45/45完整且答案正确。
- 使用当前Local v1.1/Global v1.2 low评估新增25条自然解答，117次Local与25次Global共142次调用全部完整，25/25预测过程有效；合并low 20后共278次Evaluator调用，预测44/45有效，唯一错误仍为已人工确认的Level 5 Step 7符号错误。
- 冻结同一16份人工错误解答、v1.2人工标签、新版prompt、schema和采样参数，仅将Evaluator推理强度从high改为low。首轮2个目标不完整，使用相同配置显式恢复，最终16/16有完整记录，共104次成功响应。
- 受控low结果为错误检出13/16、首错14/16、类型14/16、复核3/16；high v1.2为16/16、16/16、14/16、1/16。low出现两例不确定聚合和一例完全漏检，说明降低评估器推理强度会损害错误检出与首错稳定性。
- 旧25题high过程评估使用Local/Global v1，只保留为正确过程接受、结构遵从和v2步骤成本证据，不与新版low Evaluator作推理强度对照。

## 2026-08-31：完成low自然45题自动标记记录人工复核

- 审计确认low自然45题全部使用Local v1.1、Global v1.2与`reasoning_effort=low`；过程预测中只有1条`process_correct=false`，没有`process_correct=null`或`needs_review=true`。
- 人工复核唯一过程错误`math-test-precalculus-0488`：Step 7常数项应为负号，却写成正号，下一行无有效过渡地使用正确多项式；确认Evaluator的Step 7 `calculation_error`和`correct_answer_invalid_process`裁决正确。
- 复核答案验证层4条`manual_review_recommended`记录，均为坐标元组或LaTeX空格触发；逐坐标与参考答案一致，四面体案例也正确排除了与已知顶点重合的根，4/4确认答案正确。
- 结构化人工裁决保存于`experiments/process_evaluator_low_natural_45/human_review.json`。该范围覆盖全部自动错误与复核提示，但不覆盖44条预测有效过程，不能据此计算完整误报率或漏报率。
