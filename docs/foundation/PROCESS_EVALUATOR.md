# Hy3 Process Evaluator v1

## 目标与证据边界

Process Evaluator 位于 Solver 与最终答案验证之后，判断可见数学解答能否支撑其结论：

```text
solver response.content
        -> deterministic Step Parser
        -> per-step Hy3 Local Evaluator
        -> conservative First Error Locator
        -> one Hy3 Global Evaluator
        -> deterministic Aggregator
        -> outputs/process_evaluations.jsonl
```

正式数学证据只包括题目、`response.content`及从它确定性切分出的步骤。Solver 的`reasoning_content`、Evaluator 自身的`reasoning_content`和benchmark的`reference_solution`均不参与过程判定。最终答案验证保持独立；`answer_correct`只在无LLM聚合阶段读取，不能作为Local或Global判断过程正确的证据。

当前版本不包含人工标注有效性benchmark、multi-agent voting、ensemble、模型置信度、自动步骤类型或依赖关系。

## 模块与版本

- `process_evaluation/step_parser.py`：`process-step-parser-v1`，确定性保留步骤原文、完整`response.content`和结构问题。
- `process_evaluation/prompt.py`：当前为`math-process-evaluator-v1.1`与`math-global-evaluator-v1.2`。两者共享“先定位最早主要错误事件、再分类”的错误类型定义；Global继续使用严格的最终答案支持度语义。历史实验仍按各自记录的旧prompt版本统计，不回写结果。
- `process_evaluation/schema.py`：严格解析Local/Global可见JSON；Markdown围栏、缺字段、多余字段、非法枚举或错误step ID均失败，不做静默修复。
- `process_evaluation/aggregator.py`：`process-evaluation-aggregator-v1`，无LLM聚合与保守首错定位。
- `process_evaluation/runner.py`：读取Solver inference、逐次调用、增量保存原始响应并输出最终记录。

## Step Parser

Parser识别行首的`Step N`，兼容v1的`Step 1:`、Markdown加粗，以及v2预留的`Step 1 [Label]:`形式。每个步骤只含两个字段：

```json
{"step_id": 1, "text": "原始步骤正文"}
```

它不会补编号、合并重复步骤、重写LaTeX、判断步骤类型或判断数学正确性。结构问题包括：

- `no_numbered_steps`
- `non_contiguous_step_numbers`
- `duplicate_step_number`
- `empty_step_content`
- `final_answer_missing`
- `empty_final_answer`

显式`Final Answer:`或`Answer:`正文会与最后一个Step分离。为兼容math-solver-v1，没有显式标签时允许把最后一个完整原始`\boxed{...}`片段记录为`final_answer_text`；两者都不存在才报告缺失。重复步骤号会使本次过程评估跳过，避免把LLM结果错误归到同一个step ID；其他结构问题完整保留并触发复核。

## Local Step Evaluation

第i次Local调用只能看到完整题目、此前可见步骤和当前步骤。状态固定为：

- `valid`：推导或计算成立，且文本提供足够证据。
- `invalid`：存在明确数学错误。
- `insufficient`：结论可能正确，但缺少确认它所需的关键可见依据。
- `uncertain`：当前信息不足以可靠选择前三者。

`importance`固定为`low/medium/high`。`error_origin`固定为：

- `none`：当前步骤没有错误来源。
- `current_step`：当前步骤引入错误或关键缺口。
- `inherited`：当前操作在沿用此前错误值时局部成立，不构成新的源头错误。
- `uncertain`：无法可靠定位来源。

错误类型枚举保持固定：

| 类型 | 定义 |
| --- | --- |
| `problem_misinterpretation` | 可见解答把任务、已知信息、所求对象或操作表示错误 |
| `condition_omission` | 没有执行定义域、符号、边界、非零性、整数性、不同性或定理适用条件 |
| `case_omission` | 在丢弃其他可能或声称完整前，没有覆盖必要分支、候选根或解族 |
| `concept_or_theorem_error` | 明确陈述或直接依赖错误的一般定义、定理、恒等式、概念或规则 |
| `invalid_derivation` | 当前具体逻辑或代数结论不由可见前提推出 |
| `calculation_error` | 运算形式有效，但具体计算、化简、代入、符号或抄写执行错误 |
| `insufficient_justification` | 没有确定错误或可识别遗漏，但关键结论缺少必要可见依据 |
| `answer_extraction_or_format_error` | 前述实质推导正确、完整、充分，唯一错误位于最终答案提取、选择、抄写或格式 |
| `other` | 明确存在但无法归入上述类别的问题 |

分类不按类别表的排列顺序搜索错误。Evaluator必须先定位与当前评价目标相关的最早主要错误事件，排除继承错误和下游症状，然后才使用定义、排他边界与诊断问题选择唯一标签。所有判断只依据可见文本，不推测Solver内心是否理解某条规则。

主要排他边界为：缺失替代分支或候选属于`case_omission`，没有执行可接受性限制属于`condition_omission`；明确错误的一般规则属于`concept_or_theorem_error`，具体不成立的推导属于`invalid_derivation`，合法运算的具体执行失误属于`calculation_error`。如果非法变换先导致解丢失，主要错误是该处`invalid_derivation`，后续少解只是症状。只有前述数学过程已经正确且充分时，才使用`answer_extraction_or_format_error`。

输出字段严格为`step_id/status/importance/purpose/error_type/error_origin/evidence`，不含概率或置信度。`purpose`与`evidence`要求简洁可审计，不要求模型输出详细内部思考。

## Global Evaluation 与聚合

Global调用读取题目、完整可见解答和已验证的Local结果，检查遗漏case、全局条件、循环论证、跨步骤跳跃、题目覆盖和最终答案是否受到可见推导支持。它不读取`answer_correct`或参考解答。

`final_answer_supported=true`当且仅当可见推理过程在数学上有效、信息充分，并且能够推出最终答案。只要存在影响结论的错误前提或推导、关键证据缺失、过程不完整，或者最终答案不由可见推导推出，就必须为false。错误答案与一条错误链条“局部一致”不构成数学支持。严格schema同时要求`final_answer_supported=true`只能与`global_status=valid`及`process_complete=true`共同出现。

首错定位优先选择第一个`error_origin=current_step/uncertain`的明确`invalid`，或第一个`importance=high`的关键`insufficient`。继承错误不会成为新的首错；普通低影响证据不足不会自动成为致命首错。Global override与Local首错同时保留；两者冲突时最终首错置空并要求复核。

聚合器综合Local错误、关键证据缺口、Global完整性、最终结论支持度和不确定状态。高影响不确定或Local/Global冲突优先输出`process_correct=null`与`needs_review=true`。支持以下答案—过程关系：

- `correct_answer_valid_process`
- `wrong_answer_invalid_process`
- `correct_answer_invalid_process`
- `wrong_answer_valid_or_supported_process`
- `uncertain`

因此`answer_correct=true`与`process_correct=false`可以同时成立。

## 输出与恢复

默认文件：

- `outputs/process_evaluator_responses.jsonl`：每次Local/Global调用的prompt、请求配置、原始provider响应、可见content、内部reasoning、usage和错误；不包含解析后的评估结果。
- `outputs/process_evaluator_responses_stream_events.jsonl`：增量SSE事件与中断证据。
- `outputs/process_evaluations.jsonl`：Step Parser、已验证Local/Global结果、首错、聚合结论和已有答案正确性元数据。

三类文件均被Git忽略。JSON解析失败时原始响应已经先行落盘，最终记录写入`schema_validation_failed`并标记`evaluation_status=incomplete`，不会修成有效结果。默认resume跳过已有记录（包括不完整结果），只有显式`--retry-incomplete`才重新调用；默认`max_retries=0`。

## 记录内容与适用边界

当前链路保存的信息可以分为四层：

| 层次 | 主要信息 | 能回答的问题 |
| --- | --- | --- |
| Solver证据 | 题目、唯一`inference_id`、完整`response.content`、步骤与最终答案、prompt和生成配置 | Solver公开了哪些数学依据，这次生成是否完整 |
| 确定性解析 | 原始`response.content`、逐步原文、最终答案文本及结构问题 | Evaluator实际按哪些Step读取证据，结构是否可评估 |
| Local/Global判断 | 每步状态、重要性、目的、错误类型、错误来源、简洁证据，以及全局完整性、结论支持度和首错override | Evaluator在每个步骤和整体层面作了什么判断，判断依据是什么 |
| 确定性聚合 | Local首错、Global override、`process_correct`、答案—过程关系和`needs_review` | Local、Global与独立答案正确性如何合并成最终记录 |

原始Evaluator调用另存prompt、请求配置、模型可见JSON、内部reasoning、usage、耗时、完成状态和`evaluator_call_id`。这使JSON解析失败和调用异常仍然可审计。Evaluator内部`reasoning_content`不是正式判断依据，也不需要复原成公开chain-of-thought；schema中的`purpose`和`evidence`才是面向审计的简洁解释。

这套信息已经足够反映“可见推理—逐步评价—全局评价—确定性聚合”的运行过程，但不等于已经证明Evaluator判断正确。当前聚合记录可通过`run_id/inference_id/stage/step_id`与原始调用关联；若后续需要把多次Evaluator运行作为可独立交换的数据集，还应在聚合记录中补充Solver prompt版本、`response.content`哈希和Local/Global `evaluator_call_id`，避免只能依赖跨文件连接恢复完整实验来源。

## 与标准答案结合的有效性验证

必须区分三种“标准”信息：

1. benchmark的`reference_answer`只给出最终结论。它可以验证`answer_correct`，不能证明中间步骤有效、证据完整或首错位置正确。
2. benchmark的`reference_solution`是一条参考解法。它可以帮助标注者核对必要条件和计算，但数学题可能存在不同的正确方法，因此不能把文本或步骤对齐程度直接当作过程真值，也不应作为当前Evaluator的隐藏评分模板。
3. Process Evaluator有效性需要独立的人工过程标注。标注必须绑定到一份冻结的`response.content`，并至少记录逐步状态、关键错误类型与来源、首个致命错误、全局完整性、最终答案是否被过程支持，以及需要复核的歧义。

因此，当前Solver与Evaluator输出已经基本具备“预测侧”字段，但当前25题实验没有“真值侧”错误过程：50条解答最终答案均正确，322次Evaluator调用也全部判为valid。它能验证工程可运行、JSON遵从和正确过程上的结构稳定性，不能估计`invalid/insufficient`准确率、错误类型准确率或首错定位准确率。

后续验证应先建立少量受控过程：从冻结的正确可见解答出发，每例只注入一个已知的计算错误、非法推导、关键证据缺口、条件遗漏或case遗漏，并保留下游继承步骤；同时包含“答案正确但过程错误/不充分”的样本。正式有效性实验再增加自然产生的错误解答和独立人工裁决。参考解答只作标注辅助，最终答案只作独立结论标准，二者都不能替代人工过程标注。

建议后续人工过程标注至少包含：

```text
case_id / source_inference_id / solver_prompt_version
visible_solution_version / annotation_version / adjudication_status
steps[].step_id / annotated_status / annotated_importance
steps[].annotated_error_type / annotated_error_origin / annotation_evidence
annotated_first_error_step / annotated_global_status
annotated_process_complete / annotated_final_answer_supported / annotated_process_correct
```

受控错误阶段仍属于小规模基础行为验证，不在当前阶段扩展为multi-agent voting、ensemble或正式Evaluator validity benchmark。

## CLI

只解析和展示一个已有inference，不调用API：

```bash
uv run python -m process_evaluation.runner --dry-run --id math-test-algebra-0024
```

默认只评估一个待处理inference：

```bash
uv run python -m process_evaluation.runner --inference-id <inference-id>
```

显式重试不完整的过程评估：

```bash
uv run python -m process_evaluation.runner \
  --inference-id <inference-id> \
  --retry-incomplete
```

Evaluator v1默认使用temperature 0.1、high reasoning、8000最大输出tokens、300秒流读取timeout和0次自动重试。这是初始工程默认值，不是已经冻结的正式实验参数；批量评估前仍需小规模验证完成率、JSON遵从率、成本和延迟。
