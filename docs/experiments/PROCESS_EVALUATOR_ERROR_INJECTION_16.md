# Process Evaluator 16例受控错误集

## 1. 目标与构成

本轮从45题`math-solver-v2`候选池中选择16道不同源题，构造用于Process Evaluator错误检测、错误类型归类、首错定位和答案—过程独立性测试的受控错误集。数据构造、离线校验和首轮Process Evaluator评估均已完成。

此前`math-test-prealgebra-0485`的Level 4概念错误探针不重复计入这16道新源题，但已作为4个历史已评估变体纳入统一受控错误池。统一索引位于`experiments/process_evaluator_controlled_error_pool/`，合计20个案例、17道不同源题，当前20例均已评估。

分层构成为：Level 1-3各2题；Level 4-5各5题，其中每层4个常规错误案例，另各1个“最终答案正确但过程错误”案例。因此满足基础14题加Level 4/5额外2题的选择要求。

为避免`insufficient_justification`与“结论本身错误”混淆，Level 3最大面积题保留正确答案2500，只删除证明最大性的关键依据。因此本数据集最终共有3个正确答案但无效或不充分过程案例：Level 3、4、5各1个；Level 4/5要求的两例均已包含。

## 2. 逐例设计

| Level | 样本 | 学科 | 注入错误 | 预期类型 | 首错 |
| --- | --- | --- | --- | --- | ---: |
| 1 | `algebra-0024` | 代数 | 把同底数幂相乘写成指数相乘 | `concept_or_theorem_error` | Step 2 |
| 1 | `precalculus-0167` | 微积分预备 | 把z坐标中点算成2 | `calculation_error` | Step 3 |
| 2 | `algebra-1050` | 代数 | 颠倒函数复合顺序 | `problem_misinterpretation` | Step 2 |
| 2 | `prealgebra-0058` | 预备代数 | 过程得到选项C，但最终输出数值34 | `answer_extraction_or_format_error` | Global |
| 3 | `counting_and_probability-0280` | 计数与概率 | 忽略“至少选择一个”，保留空集 | `condition_omission` | Step 3 |
| 3 | `algebra-0422` | 代数 | 直接断言50×50最大而不给最大性依据 | `insufficient_justification` | Step 3 |
| 4 | `counting_and_probability-0187` | 计数与概率 | 把组合数`C(7,4)`算成28 | `calculation_error` | Step 3 |
| 4 | `geometry-0261` | 几何 | 用周长代替半周长套用内切圆公式 | `concept_or_theorem_error` | Step 5 |
| 4 | `intermediate_algebra-0298` | 中级代数 | 漏掉全部负有理根候选 | `case_omission` | Step 2 |
| 4 | `precalculus-0028` | 微积分预备 | 忽略`E`不能等于`D`的条件 | `condition_omission` | Step 4 |
| 4 | `algebra-0442` | 代数 | 乘负数时不反转不等号，但保留正确答案28 | `invalid_derivation` | Step 5 |
| 5 | `counting_and_probability-0273` | 计数与概率 | 错用德摩根律，把交集写成并集 | `concept_or_theorem_error` | Step 2 |
| 5 | `intermediate_algebra-0308` | 中级代数 | 只处理`y=0`，漏掉`x=-1`分支 | `case_omission` | Step 4 |
| 5 | `intermediate_algebra-0082` | 中级代数 | 幂和恒等式使用错误符号 | `invalid_derivation` | Step 5 |
| 5 | `precalculus-0488` | 微积分预备 | 保留负根`r=-6`，忽略半径为正 | `condition_omission` | Step 9 |
| 5 | `number_theory-0456` | 数论 | 错解质因数指数约束并推出168，但保留正确答案42 | `invalid_derivation` | Step 3 |

共覆盖8种固定错误类型，不使用兜底`other`：概念或定理错误3例、非法推导3例、条件遗漏3例、计算错误2例、case遗漏2例，以及题意误解、关键依据不足、答案格式错误各1例。

## 3. 构造与校验结果

- 16例来自16道不同源题，原45题输出未修改。
- 注入记录保持原v2 Step边界；合成记录明确标记为受控输入，不冒充provider响应，内部`reasoning_content`为空。
- Solver parser为16/16无警告；Process Step Parser为16/16结构成功、无结构问题；所有预设首错Step均实际存在。
- 离线最终答案验证与预期16/16一致：13例答案错误，3例答案正确但过程无效或依据不足。
- Level 4正确答案案例为不等号方向错误后仍输出28；Level 5正确答案案例为错误枚举得到168后仍输出42。两例预期关系均为`correct_answer_invalid_process`且`final_answer_supported=false`。

机器可读构造与校验见`experiments/process_evaluator_error_injection_16/cases.jsonl`、`manifest.json`和`analysis.json`。完整注入解答与离线答案验证保存在被Git忽略的`outputs/process_evaluator_error_injection_16_*.jsonl`。

## 4. 标签边界

每例预期标签是人工构造标签，不是Evaluator输出。除答案格式案例由Global发现外，其余案例均指定Local首错Step、`invalid/insufficient`状态、重要性、错误类型与`current_step`来源。后续沿用错误结果的步骤应标为`inherited`，不能重复成为首错。

Level 3关键依据不足案例预期Local状态为`insufficient`、Global状态为`insufficient`、`process_complete=false`。答案格式案例没有Local首错Step，预期由Global给出`answer_extraction_or_format_error`；如果聚合器因Global错误没有对应Step而要求人工复核，属于当前规则的预期行为。

## 5. 首轮Process Evaluator结果

使用Hy3、Local prompt v1、Global prompt v1.1、temperature 0.1、high reasoning、`max_tokens=8000`、300秒网络读取timeout和0次自动重试。79个Local判断与16个Global判断共95次调用，95/95请求成功、生成完整且通过严格JSON解析。

| 指标 | 命中 |
| --- | ---: |
| 过程错误检出 | 16/16 |
| 首错Step exact match | 14/16 |
| 错误类型 exact match | 11/16 |
| Local状态 exact match | 13/15 |
| Local错误类型 exact match | 10/15 |
| Local错误来源 exact match | 13/15 |
| Global状态 exact match | 16/16 |
| `process_complete` exact match | 9/16 |
| `final_answer_supported` exact match | 16/16 |
| `process_correct` exact match | 16/16 |
| 答案—过程关系 exact match | 16/16 |
| `needs_review` | 3/16 |

三个正确答案但无效或不充分过程案例均被识别为`correct_answer_invalid_process`，且`final_answer_supported=false`。因此本轮对“不能仅凭正确答案接受过程”的核心行为是3/3符合预期。

95次调用共使用213,477 total tokens，其中119,905 completion tokens、109,531 reasoning tokens；累计调用延迟约1,095.1秒。Local为79次、163,152 total tokens；Global为16次、50,325 total tokens。

### 主要偏差

- Level 3空集案例在注入文本中明确写出“这忽略了至少一个的要求”，Local将其理解为正确指出问题，因此没有定位Step 3；Global改判为最终答案格式/提取错误。
- Level 4排除顶点案例同样主动承认`E=D`违反条件，Local把Step 4当作有效核对，Global将类型归为答案格式错误，而不是预期的条件遗漏。
- Level 5负半径案例中，Local把Step 7从等式整体乘以`-1`误判为计算错误，产生虚假的更早首错；Global仍把Step 9选负半径作为首错，Local/Global冲突导致复核。
- 两个代数恒等/指数案例分别在`invalid_derivation`与`concept_or_theorem_error`、`calculation_error`之间发生分类边界差异。
- `process_complete`只有9/16与人工预期一致。Evaluator倾向把题意误解、格式错误、遗漏case或条件的过程同时判为不完整；该字段的人工口径需要在下一轮前进一步冻结。

### 结果边界与下一步

本轮注入文本中多处直接使用“incorrect”“overlooks”“erroneous”等自我揭示措辞，使错误检测和类型判断比自然错误更容易，因此16/16检出率不能作为自然错误准确率。所有首轮结果保留，不回写预测或人工标签。

若继续验证，应先生成去除自我揭示措辞的受控集v1.1，并重新人工核对唯一源头错误；这会需要新一轮接近95次Evaluator调用，必须单独确认额度。机器可读结果见`experiments/process_evaluator_error_injection_16/evaluation_analysis.json`。

## 去提示化版本 v1.1

已另建`experiments/process_evaluator_error_injection_16_v1_1/`，不覆盖首轮v1及其评估结果。v1.1保留相同16道源题和整体错误设计，将错误直接写成解题者会给出的数学陈述、计算或选择，删除“incorrect”“overlooks”“omit”“erroneous”等自我诊断措辞以及承认推导无效的元叙述。后续人工复核仅修正了复数遗漏分支案例在v1.1自然措辞下的首错位置；v1原文及其标签不变。

全部16条评估器可见解答已经逐例语义复核并通过本地短语扫描：自我揭示命中0条，Solver解析警告0条，过程结构异常0条，离线答案预期匹配16/16（13条错误答案、3条正确答案但过程错误）。

## 6. v1.1完整评估结果（与v1严格分开）

用户确认后，已对v1.1单独运行完整Process Evaluator。旧v1的95次结果、原始响应和`evaluation_analysis.json`均未覆盖、未混入本节；旧v1明确是含自我揭示措辞的历史行为探针，本节只统计去提示化v1.1。

配置仍为Hy3、Local `math-process-evaluator-v1`、Global `math-global-evaluator-v1.1`、temperature 0.1、top-p 1、high reasoning、`max_tokens=8000`、300秒timeout、0次自动重试。

| 指标 | v1.1结果 |
| --- | ---: |
| 计划成功调用 | 95/95 |
| Local / Global | 79 / 16 |
| 过程错误检出 | 15/16 |
| 首错Step exact match | 14/16 |
| 错误类型 exact match | 9/16 |
| Local状态 exact match | 15/15 |
| Local重要性 exact match | 15/15 |
| Local错误类型 exact match | 8/15 |
| Local错误来源 exact match | 14/15 |
| Global状态 exact match | 16/16 |
| `process_complete` exact match | 13/16 |
| `final_answer_supported` exact match | 16/16 |
| `process_correct` exact match | 15/16 |
| 答案—过程关系 exact match | 15/16 |
| `needs_review` | 3/16 |

本轮使用214,530 total tokens（93,304 prompt、121,226 completion，其中110,592 reasoning），有效调用累计延迟约1,056.7秒。另有16次最初的沙箱连接失败，无模型响应和token；原始响应文件共111条，成功完整调用95条，失败尝试16条，未将失败尝试计入有效评估分母。

runner的聚合JSONL采用追加式续跑，因此包含16条首次不完整记录和随后16条完整记录；分析脚本按`inference_id`取最后的完整记录，最终样本数仍为16，不能按聚合JSONL物理行数重复计数。

表中数值已按人工复核后的gold重算。复核前报告的首错15/16不再作为最终结果；修正复数案例的首错Step和完整性标签后，首错为14/16，同时Local状态、重要性、类型及`process_complete`指标相应变化。错误类型9/16不变，仍反映`problem_misinterpretation`、`condition_omission`、`case_omission`、`concept_or_theorem_error`及`invalid_derivation`之间的边界。

### 6.1 三条人工复核结论

| 案例 | 主要错误来源 | 是否属于Evaluator实质失败 |
| --- | --- | --- |
| 选择题格式 | Solver最终输出不符合A–E要求，且schema不能把`final_answer`表示成错误位置 | 基本不是；Evaluator判断正确 |
| 复数遗漏分支 | 原人工gold首错位置不准确，同时Evaluator对遗漏何时成为错误存在分歧 | 部分是 |
| 负半径 | Local假阳性以及Local/Global首错冲突 | 是 |

选择题案例的数学推理完整且正确，也明确得到约34美元及choice C；但最终输出为`34`而不是要求的`C`。它继续作为真实的`answer_extraction_or_format_error`案例，人工位置记为特殊位置`final_answer`。Evaluator已正确判断过程完整、最终答案不受支持并识别错误类型；进入复核主要源于当前schema只能表示编号Step。

复数案例中，Step 4只分析合法分支`y=0`，直到Step 5声称唯一解为0时才真正排除尚未检查的`x=-1`分支。因此v1.1人工gold从Step 4修正为Step 5，`process_complete`从true修正为false。Local在Step 5识别出`case_omission`，但将来源写成`inherited`；Global又把首错提前到Step 4，说明两阶段对错误生效边界仍不一致。旧v1的Step 4原文明确要求遗漏该分支，其历史gold不作修改。

负半径案例中，Step 7的两个方程数学等价，Local将其判作计算错误属于明确假阳性。Global正确把首错恢复到Step 9，但类型仍判为`problem_misinterpretation`而非人工预设的`condition_omission`；聚合器面对Step 7与Step 9冲突采用保守复核策略。该案例是本轮最明确的Evaluator实质失败样本，也展示了Global能纠正Local位置误判、但现有聚合器无法自动消解冲突的边界。

结构化人工裁决保存在`experiments/process_evaluator_error_injection_16_v1_1/human_review.json`。逐案例预测、原始评估prompt、可见JSON、内部reasoning和流事件分别通过`evaluation_analysis.json`及对应被忽略的`outputs/process_evaluator_error_injection_16_v1_1_*.jsonl`关联。

## 7. 分类 prompt v1.2 重跑结果

在不改变题目、Solver可见解答、Step Parser、Local/Global调用流程或聚合器的前提下，使用新版分类定义重新评估同一16例。新版要求先定位最早主要错误事件，再排除继承错误和下游症状，最后用定义、排他边界和诊断问题选择类型；诊断问题不作为搜索首错的绝对优先级。模型调用完成后，16例人工类型标签也按同一版分类边界逐条复核；否则新版预测与旧版标签并不处在同一判断口径下。

v1.2使用Local `math-process-evaluator-v1.1`和Global `math-global-evaluator-v1.2`。首轮有16次连接失败，随后14道目标首轮完成，2道目标显式重试后完成；共106次成功API响应（105次Local、17次Global），原始响应122条。失败尝试不含模型响应或token，按`inference_id`取最后完整记录进行16题统计。本轮使用353,599 total tokens（134,182 reasoning tokens），累计调用延迟约1,387.4秒。完整机器可读结果见`experiments/process_evaluator_error_injection_16_v1_2/evaluation_analysis.json`，独立运行说明见该目录README和manifest。

| 指标 | v1.1 | v1.2 |
| --- | ---: | ---: |
| 过程错误检出 | 15/16 | 16/16 |
| 首错Step exact match | 14/16 | 16/16 |
| 错误类型 exact match | 9/16 | 14/16 |
| Local状态 exact match | 15/15 | 15/15 |
| Local重要性 exact match | 15/15 | 15/15 |
| Local错误类型 exact match | 8/15 | 13/15 |
| Local错误来源 exact match | 14/15 | 15/15 |
| Global状态 exact match | 16/16 | 16/16 |
| `process_complete` exact match | 13/16 | 13/16 |
| `final_answer_supported` exact match | 16/16 | 16/16 |
| `process_correct` exact match | 15/16 | 16/16 |
| 答案—过程关系 exact match | 15/16 | 16/16 |
| `needs_review` | 3/16 | 1/16 |

新版 prompt 修正或稳定了多个此前的邻近分类：题意操作顺序归为`problem_misinterpretation`，候选根和排除条件分别归为`case_omission`与`condition_omission`，复数题首错稳定在Step 5；首错定位达到16/16，Local来源达到15/15，且负半径题不再出现Step 7的Local假阳性与Local/Global位置冲突。

初始11/16是新版预测直接对照v1.1旧标签的复核前统计，不作为v1.2最终结论。按新版定义复核全部16例后，13条标签保持不变，3条修订：德摩根案例从`concept_or_theorem_error`改为`invalid_derivation`，因为可见步骤只做了具体实例上的非法补集变换；幂和恒等式及奇素数指数案例从`invalid_derivation`改为`concept_or_theorem_error`，因为它们明确陈述并使用了错误的一般规则。标签复核独立于模型预测，仍保留以下2条模型分类错误：

| 案例 | 新版人工标签 | 模型预测 | 复核结论 |
| --- | --- | --- | --- |
| `l4-algebra-0442-correct-answer-invalid-bound` | `invalid_derivation` | `calculation_error` | 未翻转不等号是保持关系失败的非法推导，不只是算术符号或誊写失误 |
| `l5-precalculus-0488-negative-radius` | `condition_omission` | `answer_extraction_or_format_error` | Step 9在筛选候选根时忽略`r>0`，Final Answer只是重复该数学选择错误 |

因此v1.2最终错误类型为14/16，Local类型为13/15。v1.1与v1.2使用各自版本的人工标签，不能把9/16到14/16的全部差异都归因于Prompt提升；可直接归因于模型行为的结论仍应结合逐例变化报告。完整标签修订与保留分歧见`experiments/process_evaluator_error_injection_16_v1_2/taxonomy_review.json`。

三个正确答案但错误过程案例仍全部得到`correct_answer_invalid_process`，`final_answer_supported`为16/16。v1.2的唯一`needs_review`仍是选择题格式案例，原因是当前schema无法将特殊位置`final_answer`表示为编号Step；它不是数学过程判断失败。v1.2结果与v1、v1.1严格分开，不回写历史结果。
