# 项目日志

本文件采用追加式记录，保留项目决策和重要实施过程。

## 2026-08-24

- 确定任务领域为数学，第一阶段优先完成基于 Hy3 的数学题分步解答应用。
- 初始 benchmark 计划为 400 题：GSM8K 100 题、MATH 250 题、AIME 50 题。
- MATH 沿用官方五级难度，每级抽取 50 题；GSM8K 不新增难度标签；AIME 作为高难竞赛题集处理。
- 确定应用输入输出和后续评测记录统一采用 JSONL，同时保留数据集特有元数据。
- 使用 `uv` 创建 Python 3.10.20 虚拟环境 `.venv`。
- 初始化 `main` 分支 Git 仓库，并建立项目协作、进展和日志文件。
- 创建并切换到 `develop` 开发分支；后续开发变更不直接提交到 `main`。
- 确认 AIME 从 2024、2025 两年各抽取 25 题。
- 通过 Hugging Face Hub 下载 GSM8K、MATH、AIME 2024 和 AIME 2025 原始数据，并记录上游 revision；尚未进行抽样或格式转换。
- 发现 MATH 官方 README 当前链接的数据副本丢失原始 train/test split；额外下载并选定保留原始 split 的 `EleutherAI/hendrycks_math` 镜像作为后续抽样来源。
- 更新协作规范：进展文件只记录阶段性里程碑和关键结论，日常实施过程继续追加到项目日志。
- 增加 `pyproject.toml` 和 `uv.lock`，使用 `pyarrow` 读取原始 Parquet 数据。
- 实现确定性 benchmark 构建脚本，固定种子为 `20260824`，按稳定样本 ID 的 SHA-256 排序抽样。
- 生成 `data/benchmark/`：GSM8K 100题、MATH五个 Level 各50题、AIME 2024/2025各25题，并提供合并后的400题 JSONL 与 manifest。
- 连续两次生成所得文件 SHA-256 完全一致；数量、唯一 ID、必填字段及分层检查均通过。
- 新增 benchmark 数据说明文档，记录实际组成、MATH 学科交叉分布、各数据集答案与参考过程特征，以及对后续答案校验和过程评估的影响。
- 确定 solver 直接通过腾讯云 TokenHub 的 OpenAI-compatible API 调用 Hy3，不再考虑 CodeBuddy 调用通道。
- 实现 Dataset Loader、Prompt Builder、独立 Hy3 Client、Response Parser 和可恢复 Runner；模型输入类型只允许 `id`、`dataset`、`problem`，不会携带标准答案或参考信息。
- solver 输出逐条记录完整请求配置（不含密钥）、可见解答、`reasoning_content`、原始 API 响应、usage、请求标识、耗时、重试错误和解析结果。
- 增加单题安全默认值、显式 `--all`、断点续跑、dry-run、环境变量样例和5项自动化测试；真实 Hy3 调用等待本机配置 `HY3_API_KEY`。
- 增加被 Git 忽略的本地 `.env` 配置方式；solver 自动加载该文件，且显式 shell 环境变量优先。
- 完成首次真实 Hy3 API 调用：`gsm8k-test-0008` 一次请求成功，HTTP 200，耗时约23.46秒，总计2027 tokens，其中推理 tokens 为1423。
- Hy3 输出7个连续编号步骤并得到45英里，与 benchmark 标准答案一致；完整原始响应、可见解答、思考字段、usage和时间信息已写入本地输出。
- 首次解析将自然语言答案整句作为候选，暴露 Markdown `**Answer:**` 格式兼容问题；更新 parser 至 `solution-parser-v1.1` 后，在不重新调用 API 的情况下从原始响应正确提取答案45，6项测试全部通过。
- 增加独立最终答案验证层，采用 `math-verify 0.9.x` 与 ANTLR 4.13.2 将参考答案和预测解析为数学表达式；验证结果按 inference 单独写入 JSONL，不覆盖 solver 原始证据。
- 审计当前 benchmark 的参考答案形态：GSM8K 100题和 AIME 50题均为整数；MATH 包含167个整数答案、37个分数/有理式、12个根式，以及元组、区间、集合、矩阵、单位、选择标签等结构化类型。
- 完成跨数据集小规模验证：沿用已有 GSM8K 结果，新增两次 MATH 分数题、一次 MATH 根式题、一次 MATH 混合数题和一次 AIME 2024 题调用；五次新增调用均一次成功，共使用8918 tokens。
- 6次 inference 的最终答案均验证正确。根式预测 `5 + 6\sqrt{2}` 对参考答案 `5+6\sqrt{2}`，混合数预测 `8\frac{4}{7}` 对参考答案 `8\frac47`；两组字符串不同但数学等价，均被标记为 `format_mismatch_but_equivalent`。结构化多答案类型暂列为人工复核范围。
- 开展第二轮 GSM8K/MATH 多格式实验，覆盖货币与千位分隔符、等价单位、分数/小数、含 π 表达式、区间和无序多根；6道目标题最终均正确，区间与多根虽自动判等仍保留人工复核标记。
- 将 parser 升级至 `solution-parser-v1.2`，修复无 `Answer:` 标签结论、主要答案后附等价单位、以及 `\(...\)` 中多个等价表达的提取；从已有原始响应重新解析后，将三条漏提取/误提取记录恢复为正确，无需再次调用 API。
- 多根题在 high reasoning 下耗尽4096 completion tokens，返回 `finish_reason=length` 且无可见答案；改用 low reasoning 后以1988 tokens 完成，根顺序不同但集合等价。保留首次截断记录为 `unverified`，后续需将截断和推理预算监控纳入批量 runner。

## 2026-08-25

- 新增 `HANDOFF.md`，面向零上下文的新会话汇总当前阶段、已完成实现、真实验证结果、运行步骤、下一优先级以及 API、密钥、截断、验证误判和本地输出等风险。
- 核对并更新 `PROJECT_PROGRESS.md`：已反映 GSM8K/MATH 多格式答案实验，当前下一目标仍是结构化答案校验、截断重试策略、扩大分层验证和固定 revision 下载脚本。
