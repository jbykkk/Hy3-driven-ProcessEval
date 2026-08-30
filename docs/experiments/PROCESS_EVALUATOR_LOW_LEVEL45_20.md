# Level 4/5 low reasoning 20题自然错误实验

## 1. 目的与范围

此前新增的Level 4/5各10题只完成了high Solver与最终答案验证：20/20生成完整、答案正确，但20份自然解答没有作为一批运行Process Evaluator。本实验复用完全相同的20题，以low推理重新生成并进行过程评估，用于观察降低推理成本后的自然错误与同题成本变化。

实验按授权分两批运行，每批包含Level 4和Level 5各5题。两批合并后恰好覆盖原固定选择的20题，无重复或遗漏。具体ID、批次和本地输出索引见`experiments/process_evaluator_low_level45_20/manifest.json`。

## 2. 配置与审计

Solver继续使用`math-solver-v2`、temperature 0.9、top-p 1、stream、`max_tokens=32000`、300秒timeout和0次自动重试；Process Evaluator继续使用当前Local/Global prompt、temperature 0.1、stream、`max_tokens=8000`、300秒timeout和0次自动重试。两者仅将`reasoning_effort`从`high`改为`low`。

运行后直接审计落盘请求字段：20条Solver记录的`reasoning_effort`唯一值为`low`，136次Evaluator原始调用的唯一值也为`low`；两个集合的非low记录数均为0。因此本报告中的解题与过程评估确定均使用低强度推理。

## 3. 总体结果

| 指标 | 结果 |
| --- | ---: |
| Solver API成功 / 完整生成 | 20 / 20 |
| parser无警告 | 20 / 20 |
| 最终答案正确 | 20 / 20 |
| Process Evaluator完整 | 20 / 20 |
| Evaluator预测过程有效 | 19 / 20 |
| 正确答案但过程无效 | 1 / 20 |
| `needs_review` | 0 / 20 |

唯一结构化答案人工复核建议是`math-test-precalculus-0028`的三元坐标；预测与参考答案均为`(5/3,5/3,5/3)`，只是LaTeX空格格式不同，数学等价验证为正确。

按难度看，Level 4为10/10答案正确、10/10过程有效；Level 5为10/10答案正确、9/10过程有效。样本量仍很小，且19条valid预测尚无完整人工过程标签，不能把95%直接解释为真实过程正确率，也不能据此确定模型从Level 5开始显著下降。

## 4. 同题high/low Solver对照

| 配置 | 总tokens | reasoning tokens | 可见步骤 | 完整且答案正确 |
| --- | ---: | ---: | ---: | ---: |
| high | 183,742 | 166,318 | 110 | 20 / 20 |
| low | 60,706 | 43,550 | 116 | 20 / 20 |

low减少123,036 total tokens，即67.0%；reasoning tokens减少73.8%。分层看，Level 4 total tokens从78,426降至28,905，减少63.1%；Level 5从105,316降至31,801，减少69.8%。

low没有减少步骤数：可见步骤从high的110增至116，但可见字符从29,649降至27,758。这说明本轮成本下降主要来自内部reasoning减少，而不是简单少写步骤。两组都是temperature 0.9下的单次生成，provider没有固定seed，因此这些数字是本次配对观察，不是稳定期望值。

此前high版本的20份自然解答没有对应的批量Process Evaluator结果，所以只能比较Solver完成率、答案、可见结构和成本，不能声称high/low过程正确率已经形成严格配对对照。

## 5. Process Evaluator调用与成本

low解答共116个可见步骤，对应116次Local和20次Global，共136次Evaluator调用；全部请求成功、`finish_reason=stop`且通过严格JSON。Evaluator共使用365,789 total tokens，其中69,610为reasoning tokens。

Evaluator总tokens高于Solver，主要因为每个Local调用都会携带题目、此前可见步骤和完整错误分类说明，且每题另有Global调用。降低Evaluator reasoning强度减少了内部推理预算，但当前逐步调用结构仍有较高prompt重复成本；本实验没有high Evaluator同题结果，不能计算Evaluator high/low降幅。

## 6. 自然错误案例

`math-test-precalculus-0488`要求求四个两两外切圆中最小圆的半径。low Solver得到正确答案`6/23`，但Step 7把Step 6等式重排为：

```text
0 = 1 + 11r/3 + 23r^2/36
```

正确的常数项应为`-1`。紧接着可见解答又直接写出正确的二次方程`23r^2 + 132r - 36 = 0`，两行之间不一致，最终仍求得正确答案。Local与Global均把首错定位为Step 7、类型判为`calculation_error`，聚合为`correct_answer_invalid_process`和`final_answer_supported=false`。该处已人工定点核对，确认是可见过程中的真实符号错误，而非Evaluator误报。

这一案例直接满足任务要求中的“最终答案正确，但过程无法支撑该结论”。它也表明只统计最终答案会漏掉low生成中的自然过程错误。

## 7. 结论边界与下一步

在这20道Level 4/5题上，low把Solver总tokens降低约三分之二，同时仍保持20/20最终答案正确；过程评估进一步暴露1个答案正确但过程错误的自然样本。因此，降低推理强度对成本分析和自然错误收集都有价值，但这批题仍未使最终答案准确率下降。

当前只人工确认了Evaluator标出的1个错误，其余19条valid预测尚未逐步标注。因此本轮不报告Evaluator准确率或误报率。下一步应先对19条valid预测做分层人工抽检，尤其检查条件、分支和关键依据遗漏；若仍需寻找最终答案错误，再以明确调用上限设计重复生成或更高难样本，而不是直接扩大为全量实验。
