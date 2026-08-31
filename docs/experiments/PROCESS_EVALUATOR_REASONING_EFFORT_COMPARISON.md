# Solver与Process Evaluator推理强度实验

## 结论

low自然Solver已经扩展到与high完全同题的45题。45/45答案正确，Solver total tokens较high减少63.5%，但发现一例答案正确、过程存在计算符号错误的自然样本。当前样本仍没有出现最终答案错误，因此只能说明在这45次单次生成中未观察到答案准确率下降，不能认定high与low总体能力相同。

low 45全部使用相同的Local v1.1、Global v1.2与low配置。45条可见过程均已完成单人复核：44条有效、1条无效，与Evaluator逐条一致；答案验证的4条坐标元组格式提示也均确认正确。

在冻结输入与新版prompt的16例受控错误上，Evaluator low相对high出现明确退化：错误检出16/16降至13/16，首错16/16降至14/16，复核1/16增至3/16；类型总命中均为14/16，但失败案例不同。这是当前最直接的评估器推理强度能力边界证据。

## 单变量边界

| 对照 | 保持不变 | 唯一变化 | 可解释结论 |
| --- | --- | --- | --- |
| 自然Solver 45题 | 同题、v2 prompt、temperature、top-p、预算、stream与重试策略 | Solver high/low | 解题结果与生成成本差异 |
| 受控Evaluator 16例 | 冻结可见解答、人工标签、新版Local/Global、schema和采样参数 | Evaluator high/low | 评估能力与成本差异 |

自然low 45的Evaluator预测不与旧25题high Evaluator直接比较，因为旧25题使用改进分类定义前的Local/Global v1。旧结果仍能说明早期评估器可以完整处理正确结构化过程，并验证prompt v2降低步骤数和评估调用量，但不承担新版分类或推理强度对照。

## 主要结果

| 指标 | high | low |
| --- | ---: | ---: |
| 自然Solver样本 | 45 | 45 |
| 完整且答案正确 | 45 | 45 |
| Solver total tokens | 311,089 | 113,594 |
| Solver reasoning tokens | 275,718 | 79,193 |
| 受控Evaluator错误检出 | 16/16 | 13/16 |
| 首错exact match | 16/16 | 14/16 |
| 类型exact match | 14/16 | 14/16 |
| `needs_review` | 1/16 | 3/16 |
| 受控Evaluator total tokens | 353,599 | 290,652 |
| 受控Evaluator reasoning tokens | 134,182 | 76,315 |

受控low有104次成功调用，high有106次，因此total tokens减少17.8%是整轮实际成本差异；按成功调用归一后，每调用total tokens约从3,336降至2,795，减少16.2%，reasoning tokens约从1,266降至734，减少42.0%。

## 后续分析边界

- 自然45题已有完整单人过程标签：真实过程正确率44/45，Evaluator在本组逐条一致。任务书口径下唯一被标记样本确有问题，真实问题1/1、误报0/1；小分母和单人复核限制必须同时报告。
- Level 1-3各只有5题，45题不足以定位稳定难度临界点。
- temperature为0.9且每个条件只有一次生成，不能把单次配对差异解释为模型期望表现。
- 受控16例是人工设计的错误探针，适合比较首错和分类行为，不代表自然错误分布。
