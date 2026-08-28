# MATH 25题Solver Prompt v1/v2与Process Evaluator对照

## 目的与实验边界

2026-08-28从纯文字MATH主集合中按固定种子`20260828`选择Level 1-5各5题，共25题。每道题分别使用`math-solver-v1`和`math-solver-v2`各生成一次，再独立运行最终答案验证与Process Evaluator v1，比较生成完成率、最终答案、步骤结构、过程可评估性、tokens和延迟。

选择规则、逐层ID和哈希见`experiments/process_evaluator_v1v2_25/manifest.json`。先前单题probe样本`math-test-algebra-0144`被排除。本轮共执行50次Solver调用和322次Evaluator调用，每个请求最多执行一次，自动重试为0。

Solver两版除prompt外使用相同参数：Hy3、stream、temperature 0.9、top-p 1、high reasoning、32000最大输出tokens和300秒流读取timeout。Process Evaluator统一使用`math-process-evaluator-v1`与`math-global-evaluator-v1`、temperature 0.1、top-p 1、high reasoning、8000最大输出tokens和300秒流读取timeout。

原始provider响应、内部reasoning和流事件只保存在被Git忽略的`outputs/`。`experiments/process_evaluator_v1v2_25/analysis.json`保存文件哈希、usage、状态和配对统计，不包含reasoning或解答正文。

## 总体结果

| 指标 | Solver v1 | Solver v2 | v2相对v1 |
| --- | ---: | ---: | ---: |
| Solver完整生成 | 25/25 | 25/25 | 相同 |
| 最终答案正确 | 25/25 | 25/25 | 相同 |
| 数学等价但格式不同 | 5 | 3 | -2 |
| Process Evaluation完整 | 25/25 | 25/25 | 相同 |
| `process_correct=true` | 25/25 | 25/25 | 相同 |
| Local状态 | 155个`valid` | 117个`valid` | 无非valid样本 |
| Global状态 | 25个`valid` | 25个`valid` | 相同 |
| 需要复核 | 5 | 0 | -5 |
| 步骤总数 | 155 | 117 | -24.5% |
| 平均/中位步骤数 | 6.20 / 6 | 4.68 / 5 | 更少 |
| 可见回答总字符 | 28,845 | 28,054 | -2.7% |
| Solver prompt tokens | 2,477 | 8,202 | +5,725 |
| Solver completion tokens | 123,402 | 119,145 | -3.45% |
| Solver总tokens | 125,879 | 127,347 | +1.17% |
| Solver累计延迟 | 1,190.9秒 | 1,185.1秒 | -0.5% |
| Evaluator调用数 | 180 | 142 | -21.1% |
| Evaluator completion tokens | 146,981 | 126,224 | -14.1% |
| Evaluator总tokens | 320,085 | 263,349 | -17.7% |
| Evaluator累计调用延迟 | 1,645.1秒 | 1,435.8秒 | -12.7% |

若把Solver和Evaluator总tokens相加，v1为445,964，v2为390,696；本轮端到端v2减少55,268 tokens，约12.4%。节省主要来自步骤减少后少做38次Evaluator调用，而不是Solver生成本身变得稳定更短。

## 分Level结果

两版每个Level均为5/5完整、5/5最终答案正确、5/5过程正确。关键成本和结构指标如下：

| Level | v1/v2平均步骤 | v1/v2 Solver completion | v1/v2 Evaluator调用 | v1/v2 Evaluator completion | v1/v2复核数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 5.4 / 4.2 | 4,398 / 8,158 | 32 / 26 | 19,583 / 14,844 | 1 / 0 |
| 2 | 5.0 / 4.4 | 4,126 / 7,622 | 30 / 27 | 17,797 / 18,094 | 2 / 0 |
| 3 | 7.0 / 4.6 | 24,755 / 19,255 | 40 / 28 | 34,198 / 23,222 | 1 / 0 |
| 4 | 6.8 / 4.6 | 30,847 / 31,369 | 39 / 28 | 33,766 / 29,078 | 1 / 0 |
| 5 | 6.8 / 5.6 | 59,276 / 52,741 | 39 / 33 | 41,637 / 40,986 | 0 / 0 |

表中的Solver与Evaluator token列是每层5题总量。v2在Level 1和2的Solver completion分别明显高于v1；在Level 3和5低于v1；Level 4近似相同。因此不能得出“v2让每道Solver回答更省token”的结论。

## 配对与长尾观察

- 25个配对中，v2步骤更少19题、相同5题、更多1题。
- v2 Solver completion tokens更少仅8题，更多17题；其总量仍略低，是因为少数长尾缩短对总和影响很大。
- v2 Evaluator completion tokens更少19题、更多6题，与步骤数减少方向更一致。
- v1和v2各有5题使用至少8000 Solver completion tokens；达到16000的样本从v1的5题降为v2的2题，但v2最大值24,490高于v1最大值19,643。
- `math-test-intermediate_algebra-0298`两版均为约18k tokens，说明其长尾不太可能仅由v1 prompt造成。
- `math-test-intermediate_algebra-0341`从v1的18,869增至v2的24,490，是“v2不保证缩短推理”的明确反例。

v2步骤减少24.5%，但可见字符只减少2.7%，说明v2的每一步平均更长、承载的推断更密集。这降低Evaluator调用数，却可能降低首错定位粒度：若一个较长步骤内部包含两个关键推断，错误只能定位到该步骤，无法进一步区分内部子推断。

## 过程可评估性结论

v2在结构适配方面优于v1：25条全部显式、连续地提供可解析步骤和Final Answer；v1有5条`final_answer_missing`结构告警，导致`process_correct=true`但`needs_review=true`。v2也以更少步骤维持了本轮全部Global `process_complete=true`与`final_answer_supported=true`，没有因压缩步骤而在这25道正确解答上产生`insufficient`。

但本轮50条解答的所有Local步骤都被Evaluator判为`valid`，两版最终答案也全部正确。因此本实验只能说明：

1. v2对正确解答的结构稳定性更好；
2. v2可以显著降低过程评估调用数和端到端tokens；
3. v2不会稳定降低Solver自身成本；
4. 本轮不能验证`invalid/insufficient`区分、错误来源或首错定位准确率，也不能据此证明v2更容易定位真实错误。

从信息充分性看，v2已经为每题提供连续Step、必要推导和显式Final Answer，Evaluator也保存逐步判断、全局判断、简洁证据与聚合结果，因此本轮足以审计整条运行链路。它不足以充当Evaluator有效性实验：官方`reference_answer`只验证最终结论，`reference_solution`也只是一条可能的正确路径；本轮没有独立的逐步人工标准标注，Evaluator的`valid`不能用Evaluator自身输出反过来证明。

后续受控错误实验需要把每个样本绑定到冻结的可见解答及其Step边界，并记录预先已知的错误注入位置、类型、来源和全局影响。这样才能计算首错exact match、状态/错误类型一致性和“答案正确但过程错误”的识别率。v2单步更密集的问题也应在该实验中单独统计：如果错误位于一个包含多个关键推断的Step内部，当前协议最多只能把它定位到该Step。

## 决策与下一步

当前建议保留`math-solver-v1`作为历史复现默认，同时把v2作为后续Process Evaluator实验的优先候选。是否正式切换，应等待一个小规模受控错误集：在相同题目与正确过程上注入计算错误、非法推导、关键跳步、条件遗漏和case遗漏，比较两版步骤边界下的首错定位精度与`insufficient`召回。

本阶段不引入multi-agent voting、ensemble或Evaluator validity benchmark扩展；下一步先验证单Evaluator在已知错误上的基本行为。
