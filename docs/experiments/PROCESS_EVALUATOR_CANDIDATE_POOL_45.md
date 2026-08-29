# Process Evaluator 45题候选池

## 1. 目的与范围

因API额度受限，项目不再扩展固定100题或纯文字MATH 250题全量实验。历史实验和输出全部保留；后续Process Evaluator开发改用已有Solver可见解答构造少量受控错误。

当前候选池统一使用`math-solver-v2`，由两部分组成：

- 先前Level 1-5各5题对照实验中的25条v2 inference；
- 新增Level 4、Level 5各10题的20条v2 inference。

因此候选池共45题，Level 1-3各5题，Level 4-5各15题。逐题来源、输出路径和`inference_id`见`experiments/process_evaluator_candidate_pool_45/index.jsonl`。

## 2. 新增20题选择

新增题目来自`data/benchmark/math_text.jsonl`，明确排除旧25题。固定种子为`20260829`；每个Level先从各个可用官方学科选择1题，再均衡补足至10题。

- Level 4覆盖7个学科：代数、计数与概率、几何、中级代数、数论、预备代数、微积分预备。
- Level 5覆盖该层候选池实际存在的6个学科：代数、计数与概率、中级代数、数论、预备代数、微积分预备；该层没有几何候选。

选择脚本、逐题ID和配置见`experiments/process_evaluator_v2_level45_20/`。

## 3. Solver与答案结果

20题均使用Hy3、`math-solver-v2`、stream、temperature 0.9、top-p 1、high reasoning、`max_tokens=32000`、300秒网络读取timeout和0次自动重试。

结果如下：

| 指标 | 结果 |
| --- | ---: |
| 目标题目 | 20 |
| API成功 | 20 |
| `finish_reason=stop` | 20 |
| parser无警告 | 20 |
| 最终答案正确 | 20 |
| 总tokens | 183,742 |
| reasoning tokens | 166,318（90.5%） |

3题为格式不同但数学等价；其中三元坐标答案`math-test-precalculus-0028`按当前结构化答案规则保留人工复核建议。其余2题分别是单位文本和等价分数格式。

受限网络环境下的首次预检产生20条`APIConnectionError`，未生成模型内容或消耗模型tokens；允许联网后按原配置执行20次，全部一次完成。错误审计记录与成功结果都保存在独立本地输出中，统计只使用20条成功inference。

## 4. 证据与使用边界

45题索引只记录来源和inference引用，不复制可见解答或内部`reasoning_content`。完整模型记录继续保存在被Git忽略的`outputs/`，后续按`inference_id`定点读取。

这45题是受控错误注入的候选池，不是Process Evaluator准确率benchmark。后续每个注入样本仍需冻结修改后的`response.content`和Step边界，并人工记录注入位置、预期逐步状态、错误类型、错误来源、首错位置、全局完整性和最终答案支持度。官方`reference_answer`只验证最终答案，不能替代过程标签。

## 5. 下一步

从45题中按错误构造目的选择少量样本，依次覆盖计算错误、非法推导或定理误用、关键证据缺口、条件遗漏和case遗漏。优先保持每个变体只注入一个源头错误，并显式保留下游继承关系以及“最终答案正确但过程错误”的对照。
