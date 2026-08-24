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
