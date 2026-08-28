# Process Evaluator v1单题可行性与Solver Prompt对照

## 目的与边界

2026-08-28使用同一道纯文字MATH题`math-test-algebra-0144`完成Process Evaluator v1真实调用，并对`math-solver-v1`与用户提供的`math-solver-v2`候选做单次探索。实验只验证工程链路、严格JSON遵从和初步可评估性；每版只有一次随机生成，且题目过程没有错误，因此不能用于估计Evaluator有效性或证明v2首错定位优于v1。

Solver两版都使用Hy3、temperature 0.9、top-p 1、high reasoning、4096最大输出tokens、300秒流读取timeout和0次自动重试。v1使用既有流式smoke inference，v2新生成一次。两版过程评估均使用`math-process-evaluator-v1`、`math-global-evaluator-v1`、temperature 0.1、high reasoning、8000最大输出tokens、300秒流读取timeout和0次自动重试。

完整provider响应、Evaluator内部reasoning和逐chunk事件仅保存在被Git忽略的`outputs/process_v1v2_probe_*.jsonl`；本文只记录聚合指标，不复制内部reasoning。

## 结果

| 指标 | Solver v1 | Solver v2 |
| --- | ---: | ---: |
| Solver步骤数 | 5 | 3 |
| 可见回答字符数 | 686 | 641 |
| Final Answer来源 | 最后完整`\boxed{}` | 显式`Final Answer:` |
| Solver prompt tokens | 92 | 321 |
| Solver completion tokens | 2,085 | 1,900 |
| Solver reasoning tokens | 1,783 | 1,633 |
| Solver总tokens | 2,177 | 2,221 |
| Solver延迟 | 32.9秒 | 19.8秒 |
| Local + Global调用数 | 6 | 4 |
| Evaluator完整且schema有效调用 | 6/6 | 4/4 |
| Evaluator prompt tokens | 5,344 | 3,579 |
| Evaluator completion tokens | 4,790 | 3,076 |
| Evaluator reasoning tokens | 4,122 | 2,603 |
| Evaluator累计调用延迟 | 55.1秒 | 34.4秒 |
| Local状态 | 5个`valid` | 3个`valid` |
| Global状态 | `valid` | `valid` |
| `process_complete` | true | true |
| `final_answer_supported` | true | true |
| 答案—过程关系 | `correct_answer_valid_process` | `correct_answer_valid_process` |
| `needs_review` | false | false |

v2的Evaluator调用数减少33.3%，prompt tokens减少约33.0%，completion tokens减少约35.8%，累计调用延迟减少约37.5%。Solver侧v2虽减少了185 completion tokens，但较长指令增加229 prompt tokens，因此本次Solver总tokens反而从2,177小幅增至2,221；不能只看回答长度判断总生成成本。

## 对适配性的判断

v2在本题中表现出三个正面变化：

- 三个步骤分别承担“展开并建立主方程”“代入条件”“隔离目标量”的连贯数学目的，Local Evaluator得到的证据边界清晰。
- 最后一步主动说明加60是可逆操作且不引入额外限制，直接响应了条件检查要求。
- 显式`Final Answer:`消除了v1需要用最后一个`\boxed{}`兼容回退的情况；更少的步骤也显著降低逐步评估调用数。

同时存在一个需要后续样本验证的权衡：v2把恒等式展开和使用`(2x+3y)^2=4`合并在Step 1，而v1将它们分成多个步骤。v2更紧凑，但如果该阶段包含错误，首错只能定位到较大的Step 1；v1可能提供更细的错误边界。因此“连贯阶段”比强制原子步骤更自然，但不能让单步同时容纳过多独立关键推断。

## 结论与下一步

Process Evaluator v1的完整链路在真实Hy3响应上可行：确定性分段成功，10次Local/Global调用全部正常结束并通过严格JSON schema，原始响应与聚合结果分离落盘，最终答案正确性与过程结论保持独立。

本次单题上v2更适合低成本过程评估，但尚不足以替换默认v1。后续应建立含正确过程、注入错误、关键跳步、条件遗漏和case遗漏的小规模受控集，比较两版的步骤边界、`insufficient`召回、首错定位粒度、最终答案质量、JSON遵从率与成本。

后续已完成Level 1-5各5题的25题分层对照，见`PROCESS_EVALUATOR_V1V2_25.md`；其结论取代本单题probe作为当前prompt比较的主要实验依据。
