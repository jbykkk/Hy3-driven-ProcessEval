# Level 4/5 low reasoning 20题实验

本实验复用`process_evaluator_v2_level45_20`的20题固定选择，将Solver和Process Evaluator的`reasoning_effort`均从`high`改为`low`，其余参数保持既有协议。

实验按用户授权分两批运行，每批包含Level 4和Level 5各5题。首批输出使用`outputs/process_low_level45_10_*`，第二批使用`outputs/process_low_level45_remaining10_*`；两批合并后恰好覆盖原20题，无重复或遗漏。完整响应、内部reasoning、Evaluator原始响应与流事件仍只保存在被Git忽略的`outputs/`。

逐记录审计确认20条Solver请求与136次Evaluator调用的`reasoning_effort`全部为`low`，非low记录为0。20/20生成完整、最终答案正确；Process Evaluator预测19/20过程有效，并在`math-test-precalculus-0488`发现Step 7计算符号错误，聚合为`correct_answer_invalid_process`。该处已人工核对为真实可见文本不一致；其余19条valid预测尚未全部建立人工过程标签，因此本实验不是Evaluator正式准确率benchmark。

配置、选择、批次和机器可读汇总见`manifest.json`与`analysis.json`；分析报告见`docs/experiments/PROCESS_EVALUATOR_LOW_LEVEL45_20.md`。
