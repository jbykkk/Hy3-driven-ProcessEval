# Level 4受控过程错误与首错定位实验

## 目的与构造

2026-08-28选择纯文字MATH Level 4样本`math-test-prealgebra-0485`：求四个最小质数乘积与四个最小合数乘积的正差，标准答案为1518。实验复用25题对照中已经生成并验证正确的`math-solver-v1`和`math-solver-v2`解答，不重新调用Solver，也不修改原始记录。

在两版可见解答中注入同一个源头错误：把1视为合数，选择`1,4,6,8`，随后一致地计算乘积192与差18。每版各构造两种最终答案：

- 正确答案变体：错误过程最后强行给出1518，用于检验`answer_correct=true, process_correct=false`。
- 错误答案变体：错误过程最后给出18，用于检验首错和下游继承错误。

四条输入均保存来源inference、Solver prompt版本、可见内容版本标识和预期标签。完整受控输入只存在于`outputs/`，跟踪目录中的`cases.jsonl`不含Solver或Evaluator内部reasoning。

## 运行配置

答案验证先得到2条correct与2条incorrect。Process Evaluator沿用v1默认候选：Hy3、Local/Global prompt v1、stream、temperature 0.1、top-p 1、high reasoning、8000最大输出tokens、300秒流读取timeout和0次自动重试。

按Step逐条调用后再做一次Global，因此v1的两个7步变体各8次调用，v2的两个5步变体各6次调用，共28次有效provider调用。首次沙箱内运行在每条首个请求前发生4次`APIConnectionError`，没有模型响应或token消耗；随后显式`--retry-incomplete`并开放外部连接，28次真实调用均一次完整，不存在成功请求的重复执行。

## 结果

| 结构 / 最终答案 | 预设首错 | Evaluator首错 | Global | `final_answer_supported` | 关系 | 结果 |
| --- | ---: | ---: | --- | --- | --- | --- |
| v1 / 1518正确 | Step 4 | Step 4，概念/定理错误 | invalid | false | `correct_answer_invalid_process` | 命中 |
| v1 / 18错误 | Step 4 | Step 4，概念/定理错误 | invalid | false | `wrong_answer_invalid_process` | 命中 |
| v2 / 1518正确 | Step 3 | Step 3，概念/定理错误 | invalid | false | `correct_answer_invalid_process` | 命中 |
| v2 / 18错误 | Step 3 | Step 3，概念/定理错误 | invalid | true | `wrong_answer_invalid_process` | 首错命中；支持度不符合新口径 |

四条均得到：

- 源头步骤`status=invalid`、`importance=high`、`error_type=concept_or_theorem_error`、`error_origin=current_step`；
- `first_error_step`与预设4/4一致，首错类型4/4一致；
- 后续基于`1,4,6,8`的乘法和差值计算被判为局部有效但`error_origin=inherited`，没有重复制造首错；
- `global_status=invalid`、`process_correct=false`及答案—过程关系4/4一致；
- 两个答案正确变体均未因`answer_correct=true`而被误判为正确过程；
- 4条均`needs_review=false`。

28次有效调用共使用29,921 completion tokens，其中27,167 reasoning tokens；总tokens为54,770，累计调用延迟310.1秒。这里的Evaluator reasoning只用于usage统计，不作为实验判定证据。

## 暴露的问题与后续统一口径

两个错误答案变体都把18从错误前提一致地推导出来，但历史Global v1 prompt对v1结构返回false、对v2结构返回true。项目现已统一口径：`final_answer_supported=true`当且仅当可见推理过程在数学上有效、信息充分，并且能够推出最终答案；与错误链条局部一致不构成支持。因此两条都应为false，历史v2结果是新口径下的不符合项。

Global prompt已升为`math-global-evaluator-v1.1`并明确上述定义，严格schema也禁止`global_status=invalid/insufficient/uncertain`或`process_complete=false`时返回支持为true。历史原始响应和本报告不回写；以后不同Global prompt版本必须分开统计。

## 结论与边界

这个探针初步证明当前Evaluator能够在v1/v2两种步骤结构中检测一个明确概念错误，正确定位源头，区分下游继承，并可靠表示“答案正确但过程错误”。v2步骤更紧凑，但本题的错误仍落在清晰独立的Step中，没有降低定位能力。

本实验只有一道题、一个人工错误类型和一次Evaluator运行，不能代表总体准确率，也没有覆盖`insufficient`、条件/case遗漏、非法推导或步骤内部多推断错误。后续只用少量不同错误类型扩展受控集，不把结果解释为正式validity benchmark。
