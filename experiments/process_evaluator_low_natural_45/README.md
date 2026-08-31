# low自然推理45题

本实验将旧25题v2的同一固定选择补充为low Solver与新版low Process Evaluator，并与已完成的Level 4/5 low 20题合并。最终Level 1-5分布为5/5/5/15/15，和high自然Solver 45题完全同题。

45条Solver请求全部为`math-solver-v2`与low，45/45完整、答案正确且无parser warning。Solver共113,594 total tokens、79,193 reasoning tokens；同题high为311,089与275,718，分别减少63.5%与71.3%。两边temperature均为0.9且每个配置每题只生成一次，因此这是配对单次样本结果。

新版low Evaluator完成233次Local与45次Global，共278次调用，全部完整；预测44条过程有效、1条过程错误。唯一错误是已人工确认的`math-test-precalculus-0488` Step 7符号不一致。其余44条尚未建立完整人工过程标签，44/45不能写成Evaluator准确率或误报率。

已复核全部自动标记记录：1条过程错误确认是真实错误；过程评估没有`needs_review=true`记录；答案验证层4条坐标元组格式复核均确认答案正确。结构化裁决见`human_review.json`。该复核没有覆盖44条预测有效过程，因此仍不能计算完整误报率或漏报率。

旧25题high过程评估使用Local/Global v1，而本实验使用Local v1.1/Global v1.2，所以两批Evaluator结果不作推理强度对照；Solver high/low仍保持除推理强度外配置一致。
