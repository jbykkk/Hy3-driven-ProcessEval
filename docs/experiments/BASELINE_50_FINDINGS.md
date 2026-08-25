# Baseline 50：实验结果、问题状态与当前决策

## 1. 文档范围

本文是当前唯一的验证问题与解决方案汇总，由原实验报告和问题决策文档合并而成。它记录50题high/4096 baseline、部分high/16000对照、问题处理状态以及由此产生的数据集调整。

当前主实验评测集已收敛为MATH 250题，官方Level 1-5各50题。GSM8K 100题和AIME 50题继续保留，但仅作补充；AIME评测暂停。仓库中的400题数据池和历史实验记录不删除。

## 2. 实验与结果

### 2.1 High/4096 baseline

固定种子`20260825`按benchmark比例选择50题：GSM8K 13题、MATH 31题、AIME 6题。请求统一使用`hy3`、thinking enabled、`reasoning_effort=high`、`max_tokens=4096`、temperature 0.9、top_p 1.0和`math-solver-v1` prompt。

| 数据集 | 题数 | `stop` | `length` | 截断率 |
| --- | ---: | ---: | ---: | ---: |
| GSM8K | 13 | 11 | 2 | 15.4% |
| MATH | 31 | 16 | 15 | 48.4% |
| AIME | 6 | 0 | 6 | 100.0% |
| 合计 | 50 | 27 | 23 | 46.0% |

- 50次请求均一次获得HTTP成功响应，无API错误或重试。
- 27条完整回答经parser v1.3离线重评后全部验证正确。
- 23条截断均为`unverified`；22条没有可见答案，1条只留下部分步骤。
- 端到端可验证正确答案产出率为27/50，即54%，不能用“完成后27/27正确”替代总体结果。

MATH分层结果：

| Level | 题数 | `stop` | `length` |
| --- | ---: | ---: | ---: |
| 1 | 7 | 5 | 2 |
| 2 | 6 | 3 | 3 |
| 3 | 6 | 5 | 1 |
| 4 | 6 | 1 | 5 |
| 5 | 6 | 2 | 4 |

50题共使用135,966 tokens；reasoning tokens为121,355，占completion tokens的93.7%。23条截断消耗97,976 tokens，占总量72.1%，串行inference延迟合计约29.2分钟。

### 2.2 High/16000部分对照

对23条截断样本计划做单变量重跑，只将`max_tokens`从4096提高到16000，并关闭自动重试。用户在保存16题后暂停，因此结果不能外推到全部23题。

| 指标 | 结果 |
| --- | ---: |
| 已保存 inference | 16/23 |
| 恢复为`stop` | 12 |
| 仍为`length` | 4 |
| 已完成样本恢复率 | 75.0% |
| 本轮总tokens | 167,169 |
| 同16题在4096轮总tokens | 68,100 |
| 平均单题延迟 | 127.8秒 |

12条完整回答中11条自动验证正确；另1条正文明确给出正确答案，但parser未识别`Conclusion:`格式。4条截断统一为`unverified`。本轮未运行到AIME，未启动24000测试，也未实现分段回答或记忆系统。

## 3. 问题处理状态

| 问题 | 当前结论或处理 | 状态 |
| --- | --- | --- |
| high/4096大量截断 | 思考与可见答案共享输出预算；4096不能作为稳定high配置 | 未解决 |
| 16000仍截断且成本上升 | 4/16仍截断；同样本token约为4096轮的2.45倍，不自动升至24000 | 待确定正式预算 |
| Asymptote图形输入风险 | solver只传题干和`[asy]`源码文本；已完成7道图形题中4道仍截断，9道非图形题全部完成 | 输入策略未定 |
| runner resume跳过截断 | HTTP成功的`length`仍记为`status=success`，会被`successful_ids()`跳过 | 未解决 |
| inference非确定性 | 样本选择固定，但temperature 0.9使推理长度和措辞可变化 | 正式配置待定 |
| 复杂结构化答案 | 集合、矩阵、单位、选择标签等尚未全面覆盖 | 未完成 |
| 截断片段被误评分 | evaluation现在只允许`finish_reason=stop`进入评分；parser候选仅审计 | **已解决** |
| parser v1.2漏提取最后步骤 | 已升级v1.3并恢复原8条结果；仍保留少量自然语言格式人工复核 | **已解决主要问题** |
| 等价答案字符串不同 | math-verify/SymPy已覆盖小数/分数、根式、常见LaTeX、区间和无序多根，并标记格式差异 | **已解决基础类型** |
| API连通性和批次稳定性 | 50题baseline无鉴权、429、网络或超时错误 | **已验证** |

腾讯官方说明思考tokens和可见回答共同计入completion tokens，`finish_reason=length`表示达到输出上限；Hy3空响应或截断场景建议`max_tokens>=16000`。本项目的16000对照说明该建议能提高完成率，但不能保证完成，也不代表成本适合全量实验。[Chat Completions字段说明](https://cloud.tencent.com/document/product/1823/135872)，[Hy3调用指南](https://cloud.tencent.com/document/product/1823/132252)

### Asymptote处理边界

MATH 250题中20题包含Asymptote源码，230题不包含。当前不能静默删除图形信息，也不能假设文本Hy3接口会接收渲染图片。正式实验需要在以下策略中明确选择，并单独报告图形子集：

1. 保留原始Asymptote源码文本；
2. 在不泄漏答案的前提下确定性转换为几何关系文本；
3. 将20题作为独立输入协议的图形子集。

## 4. 数据集使用调整

| 数据集 | 数量 | 当前用途 |
| --- | ---: | --- |
| MATH | 250，Level 1-5各50 | 当前主实验；默认solver输入 |
| GSM8K | 100 | 基础文字应用题和整数答案补充实验 |
| AIME | 50，2024/2025各25 | 保留数据，暂停当前阶段评测 |

`data/benchmark/benchmark.jsonl`仍保留400题用于追溯和未来补充实验，但不再是solver默认输入。历史跨数据集结果只作为历史证据，不进入MATH主实验分母。

## 5. 评分与实验边界

正式实验应分别报告：

1. 请求成功率；
2. 生成完成率，即`finish_reason=stop`比例；
3. 完成后正确率；
4. 全部目标样本中的端到端正确答案产出率；
5. parser成功率和人工复核率；
6. 总/平均tokens、reasoning占比和延迟。

任何`finish_reason=length`响应都标为`unverified`，即使残缺文本中存在可解析候选。不同输出上限、重试方式或输入协议必须分别记录，不能混成一个无标注分数。

当前明确不做分段回答和记忆系统；24000没有实验数据，不应自动启动。

## 6. 下一步

1. 修正solver完成状态与resume语义，区分“请求成功”和“生成完成”。
2. 明确MATH 20道Asymptote题的输入及单独报告策略。
3. 根据现有成本确定正式`max_tokens`、批次大小、超时和额度上限。
4. 完善结构化答案验证并冻结评分协议。
5. 协议稳定后才运行MATH 250题主实验；AIME保持暂停，GSM8K只在明确补充实验中使用。

## 7. 可复查材料

- `experiments/baseline_50/manifest.json`、`selection.jsonl`：50题选择、种子和校验和。
- `experiments/baseline_50/analysis.json`、`issues.jsonl`：4096轮聚合与问题记录。
- `experiments/baseline_50/high_16000_partial_analysis.json`、`high_16000_partial_issues.jsonl`：16000部分对照与问题记录。
- `outputs/baseline_50_solver_outputs.jsonl`和对应verification文件：本地完整响应，被Git忽略。

可提交的问题记录不复制完整`reasoning_content`、provider raw、响应头或请求ID；完整证据只保存在本地忽略目录。
