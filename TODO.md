# TODO

本文集中记录项目后续可能需要完成的计划、待验证假设和已知问题。它不是阶段进展或实验报告：里程碑写入 `PROJECT_PROGRESS.md`，实施历史追加到 `PROJECT_LOG.md`，稳定设计进入 `docs/foundation/`，具体实验结论进入 `docs/experiments/`。

## 过程评估与 Solver Prompt

### 目标与边界

- [x] 实现 `math-solver-v2`候选并保留v1显式版本选择，让 Hy3 的可见回答 `response.content` 更适合逐步验证；25题结构与成本对照已完成，是否升为默认仍待受控错误定位实验。
- [x] 正式过程评估只使用 `response.content`；内部 `reasoning_content` 仅作本地推理长度、循环思考和截断原因诊断。
- [x] 通过Solver输入类型边界确保prompt不包含benchmark的标准答案、参考解答、难度或其他可能泄漏答案的信息。
- [x] 明确当前信息充分性：现有记录足以审计可见解答、逐步/全局判断与聚合过程，但Evaluator预测不能作为自身正确性的标准标注。

### Prompt v2 当前协议

- [x] 保留连续的 `Step 1, Step 2, ...`，每一步承担一个连贯数学阶段并给出清晰目的或中间结果。
- [x] 要求后续实际使用的关键推导依据、适用条件、case和中间结果，避免关键位置使用无依据跳步。
- [x] 只给出一条主要解法，避免放弃的尝试、平行解法、无必要重复和元评论。
- [x] 使用稳定的 `Final Answer: \boxed{...}` 结尾，并优先采用人类可读的Markdown/LaTeX。
- [ ] 在受控错误集上评估“每步一个连贯阶段”是否过密；当前v2步骤减少24.5%但可见字符只减少2.7%，可能降低步骤内部首错粒度。
- [ ] 步骤类型、显式依赖或严格JSON只作为后续可选对照，不纳入当前v2协议，也不由Parser自动生成。

当前格式不固定步骤数量，也不强行生成不需要的验证步骤：

```text
Step 1: <one coherent stage with its purpose and intermediate result>
Step 2: <the next justified stage, including required conditions or cases>
Final Answer: \boxed{...}
```

### 已完成实现与对照

- [x] 将 prompt 模板做成显式版本选择，保留 `math-solver-v1` 作为可复现实验对照。
- [x] 新增独立确定性Process Step Parser，兼容v1及v2候选格式，保留步骤原文、完整`response.content`和结构问题，不生成步骤类型或依赖。
- [x] 定义并实现过程评估 JSONL schema：逐步判定、错误来源、首错步骤、固定错误类型、简洁证据和人工复核字段；v1不输出模型置信度。
- [x] 实现Hy3 Local/Global Process Evaluator v1、严格JSON校验、独立原始响应持久化和无LLM聚合器。
- [x] 固定MATH Level 1-5各5题的纯文字小规模对照集，共25题并覆盖7个学科；选择、配置、哈希和逐样本聚合已纳入`experiments/process_evaluator_v1v2_25/`。
- [x] 在相同生成参数下完成25题配对v1/v2单次对照；结论按配对和分Level报告，并明确temperature 0.9下不能把单题长度波动直接归因于prompt。
- [x] 完成`math-test-algebra-0144`同题单次v1/v2探索；该结果现仅保留为早期smoke，正式prompt比较以随后完成的25题分层对照为准。
- [x] 完成25题正式分层对照：两版均25/25答案与过程正确；v2消除5条结构复核、减少21.1% Evaluator调用和17.7% Evaluator总tokens，但Solver总tokens增加1.17%。
- [x] 新增与旧25题不重合的Level 4/5各10题并运行v2 Solver；20/20生成完整、答案正确，随后与旧25题v2整理为45题过程评估候选池。

### 下一阶段：过程真值与错误定位验证

- [ ] 先补充可独立交换的来源关联字段：在聚合过程记录中保存Solver prompt版本、可见解答版本标识，以及Local/Global原始调用ID或等价引用；人工标准标注必须绑定冻结的可见解答和Step边界。
- [ ] 设计独立过程标注格式与简短标注规范，覆盖逐步`status/importance/error_type/error_origin`、首个致命错误、全局完整性、最终答案支持度和裁决状态；当前不扩展为正式人工标注benchmark。
- [x] 从45题候选池建立16例分层受控错误集，覆盖8种固定错误类型；每例指定单一源头错误、预期首错与答案—过程关系，构造和离线答案验证已通过。
- [x] 专门加入“最终答案正确但过程错误/不充分”和“下游局部计算成立但继承前错”样本，验证答案—过程独立性与`error_origin=inherited`。
- [x] 完成首个Level 4受控概念错误探针：v1/v2搭配正确/错误答案共4条，过程错误、首错、类型、来源和答案—过程关系均4/4命中。
- [x] 冻结`final_answer_supported`语义：当且仅当可见过程数学有效、信息充分且能推出最终答案；错误链条的局部一致不算支持。Global prompt升为v1.1并增加schema一致性约束。
- [x] 对受控集报告四态判定、错误类型、错误来源、首错exact match、Global完整性/支持度、弃权或复核率，并按v1/v2的Step边界比较可定位粒度。
- [x] 完成16例新受控集首轮Evaluator评估：95/95调用完整，过程错误16/16、首错14/16、类型11/16、答案—过程关系16/16。
- [x] 保留已评估v1，另建去提示化v1.1；16例评估器可见文本均以自然错误陈述、计算或选择呈现，自我揭示扫描0条，人工语义复核16/16通过。
- [x] 用户确认后运行v1.1 Process Evaluator；当前状态为`complete`。
- [x] 用户确认后完成v1.1独立评估：95次有效调用（79 Local、16 Global），原始记录另含16次连接失败；旧v1输出未覆盖。
- [x] 完成v1.1三条`needs_review`人工复核：选择题为答案输出/schema位置限制，复数题修正人工gold且Evaluator仍有起点分歧，负半径为Local假阳性与阶段冲突；修正后首错14/16，未与旧v1混算。
- [ ] 扩展过程评估输出以表示`final_answer`错误位置，并明确分支遗漏何时构成首错。
- [x] 细化全部固定错误类型的定义、排他边界和诊断问题；分类前必须先定位最早主要错误事件，并排除继承错误和下游症状。
- [ ] 使用不针对现有16题的通用受控样本继续验证`invalid_derivation`与`calculation_error`、`condition_omission`与`answer_extraction_or_format_error`边界；旧结果不回写。
- [ ] 评估Local/Global首错冲突时的聚合策略。
- [x] 使用新taxonomy对同一16例受控集独立重跑，并按新版边界复核16条人工标签：错误检出16/16、首错16/16、类型14/16、`needs_review` 1/16；复核前11/16不作为最终指标，旧实验保持分离。
- [ ] 为`final_answer`建立可审计的特殊错误位置表示，并用通用而非针对现有16题的受控样本继续验证类型边界。
- [x] 清理注入文本中会主动暴露错误的措辞，重新核对唯一源头错误与`process_complete`人工口径，并完成独立v1.1评估。
- [x] 将旧Level 4的4个已评估变体纳入统一受控错误池，同时保留其独立实验记录和历史Global口径差异。
- [ ] 官方`reference_answer`仅验证最终结果；`reference_solution`只作为标注者核对条件和覆盖面的辅助，不做逐步标准答案，也不进入当前Local/Global prompt。
- [ ] 受控集验证通过后，再规划含自然错误解答和独立人工裁决的正式Evaluator validity benchmark；当前阶段不实现multi-agent voting或ensemble。
- [ ] 同时报告最终答案正确率、生成完成率、步骤解析成功率、首错可定位性、reasoning/可见回答tokens、延迟和成本。
- [ ] 人工抽检v2是否制造空步骤、遗漏必要推导，或让过程看似规范但无法支撑结论。
- [ ] 只有在最终答案质量不下降、过程更易评估、首错粒度可接受且成本可控时，才将v2升为后续实验默认prompt。

## 生成协议与运行稳定性

- [x] 区分`request_status`和`generation_status`；默认resume跳过已有成功请求（包括截断），只有显式`--retry-incomplete`才重跑不完整生成，防止相同参数自动循环调用。
- [x] 当前生成协议候选固定为SSE流式调用、high reasoning、`max_tokens=32000`和300秒网络读取timeout。
- [x] 在新增Level 4/5共20题上验证候选协议：20/20一次完整，总tokens 183,742，其中reasoning占90.5%；继续保持默认0次自动重试。
- [x] 新建`math_text.jsonl`，按Level确定性替换原选择中的20道Asymptote题；原`math.jsonl`及图形题完整保留，Solver默认从纯文字候选池安全选择。
- [x] 因API额度成本取消MATH每Level 50题、共250题的全量评测方案；保留数据和标签，后续只做有明确问题、样本数和额度上限的小规模实验。
- [x] Process Evaluator v1不读取`reference_solution`，因此13条参考解答中的Asymptote插图不会进入Local/Global prompt；以后若引入参考解答辅助模式再单独设计。
- [x] 将部分chunk增量写入独立事件JSONL，以`stream_started`、`stream_completed`、`stream_incomplete`和`stream_interrupted`区分状态；只有完整生成进入正式评分。
- [ ] 评估逐chunk事件文件的存储开销，必要时采用批量刷新或压缩，但不得损失中断证据。

## 答案验证与数据复现

- [ ] 为多答案、集合、区间、矩阵、单位及选择题标签增加分类型校验。
- [ ] 实现固定上游 revision 的可复现下载脚本。
