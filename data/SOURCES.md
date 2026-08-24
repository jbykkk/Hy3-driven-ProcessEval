# 原始数据来源

原始文件下载到 `data/raw/`，该目录不提交 Git。本文件记录用于复现下载的数据仓库与 revision。

| 数据集 | Hugging Face 仓库 | Revision | 本地目录 | 备注 |
| --- | --- | --- | --- | --- |
| GSM8K | `openai/gsm8k` | `740312add88f781978c0658806c59bc2815b9866` | `data/raw/gsm8k/` | 使用 `main` 配置的 `test` split |
| MATH | `EleutherAI/hendrycks_math` | `21a5633873b6a120296cce3e2df9d5550074f4a3` | `data/raw/math_eleutherai/` | 保留七个学科配置及原始 train/test split；后续只从 test 抽样 |
| AIME 2024 | `math-ai/aime24` | `83a7f387baaa524a8bda0022eac0541582297103` | `data/raw/aime24/` | test split，共 30 题 |
| AIME 2025 | `math-ai/aime25` | `563bb8404243c5f09de6ec262f2db674fe5bce9b` | `data/raw/aime25/` | test split，共 30 题 |

## MATH 来源说明

MATH 官方仓库当前 README 链接的 `qwedsacf/competition_math` revision `e839825f9ec5c6cfa585c654a59610969ec13993` 已下载到 `data/raw/math/` 用于核验。该版本将 12,500 题合并为单一 `train` 文件，未保留原始 train/test split，因此 benchmark 抽样改用保留原始 split 的 `EleutherAI/hendrycks_math` 镜像。

## 下载原则

- 下载时固定上述 revision，避免上游更新造成数据漂移。
- 原始文件只读保存；筛选、格式转换和校验写入其他目录。
- benchmark 生成脚本需记录抽样种子、源 split 和稳定样本标识。
