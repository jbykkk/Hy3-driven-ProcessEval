# Hy3 Solver 设计与使用

## 目标

第一阶段 solver 负责从 benchmark 读取数学题，调用 Hy3 生成可见的分步解答，并将一次 inference 的请求、原始响应、解析结果、用量、时间和错误完整写入 JSONL。此阶段不进行答案评分或过程正确性评估。

## 架构

```text
data/benchmark/math.jsonl（当前主实验）
              |
              v
       Dataset Loader
       仅保留 id/dataset/problem
              |
              v
        Prompt Builder
        math-solver-v1
              |
              v
          Hy3 Client
   OpenAI-compatible Chat API
              |
              v
        Raw API Response
              |
              +------------------+
              |                  |
              v                  v
      Response Parser      原始响应原样保存
              |                  |
              +--------+---------+
                       v
       outputs/solver_outputs.jsonl
```

模块职责：

- `solver/dataset.py`：只生成 `SolverSample(id, dataset, problem)`，从类型边界上阻止参考答案、参考解答和 metadata 进入模型请求。
- `solver/prompt.py`：集中维护 prompt 模板与版本号。
- `solver/client.py`：独立封装 Hy3 API 鉴权、请求参数和完整响应读取，不包含 benchmark 逻辑。
- `solver/parser.py`：从可见回答中提取编号步骤和候选最终答案；不修改原始响应。
- `solver/runner.py`：负责样本选择、断点续跑、重试、计时和逐条追加 JSONL。

## Prompt v1

```text
Solve the following mathematics problem. Provide a clear step-by-step solution. Number the steps explicitly as Step 1, Step 2, Step 3, ... Do not skip important reasoning or calculations.

Problem:
{problem}
```

prompt 中不包含 `reference_answer`、`reference_solution`、难度、学科或其他参考 metadata。

runner 默认读取 `data/benchmark/math.jsonl` 的250题。GSM8K、AIME或400题合并数据仍保留，但只有显式传入相应 `--input` 时才使用；AIME当前暂停评测。

## API 配置

solver 使用腾讯云 TokenHub 的 OpenAI-compatible Chat Completions API。默认参数：

| 参数 | 默认值 |
| --- | --- |
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model | `hy3` |
| Temperature | `0.9` |
| Top P | `1.0` |
| Max output tokens | `4096` |
| Thinking | `enabled` |
| Reasoning effort | `high` |
| Stream | `false` |
| Timeout | `300s` |

注意：`4096` 是初始 smoke test 默认值。50题 baseline 在 high reasoning 下出现23/50截断；随后16条已完成的high/16000对照仍有4条截断，而且token消耗约为同样本4096轮的2.45倍。代码默认值暂未改动；执行较大批次前必须阅读 `docs/experiments/BASELINE_50_FINDINGS.md`，并显式确认输出预算和额度风险。

solver 会自动读取项目根目录中被 Git 忽略的 `.env`。把本地密钥写入：

```dotenv
HY3_API_KEY="your-tokenhub-api-key"
HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
HY3_MODEL="hy3"
```

已在 shell 中设置的环境变量优先于 `.env`。也可以不使用文件，直接导出环境变量：

```bash
export HY3_API_KEY="your-tokenhub-api-key"
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"  # 可省略
export HY3_MODEL="hy3"                                    # 可省略
```

## 安全测试

先执行 dry-run。默认只展示第一题的模型可见输入，并且不会访问 API：

```bash
uv run python -m solver.runner --dry-run
```

真实单题调用同样默认只运行第一条待处理样本：

```bash
uv run python -m solver.runner
```

指定样本或少量题目：

```bash
uv run python -m solver.runner --id math-test-algebra-0024
uv run python -m solver.runner --limit 3
```

补充数据集必须显式指定输入，例如：

```bash
uv run python -m solver.runner \
  --input data/benchmark/gsm8k.jsonl \
  --id gsm8k-test-0008
```

只有显式传入 `--all` 才会运行所有未完成样本，避免误消耗额度：

```bash
uv run python -m solver.runner --all
```

## 断点续跑与错误处理

- 每完成一道题立即追加并刷新一行输出，进程中断不会丢失已完成记录。
- 默认读取已有输出，跳过 `status=success` 的样本。
- 失败记录也会写入 JSONL，但下次运行仍会重试该样本。
- 默认最多重试两次，记录每次失败的异常类型和消息。
- `--no-resume` 可关闭成功样本跳过行为，适合重复实验；新结果会追加而非覆盖。

## 输出记录

每行对应一次 inference，主要字段包括：

```text
schema_version
run_id / inference_id
status
sample.id / sample.dataset / sample.problem
prompt.template_version / prompt.messages
request（不含 API Key）
timing.started_at / finished_at / latency_ms
attempt_count / attempt_errors
response.http_status / headers / provider_response_id
response.content / reasoning_content / usage / raw
parsed.parser_version / steps / final_answer / warnings
```

`response.raw` 保存 SDK 解析后的完整 API 响应；`response.content` 是后续过程评估的主要对象；`reasoning_content` 单独保存，但不与模型面向用户给出的可见解答混为一谈。运行输出位于被 Git 忽略的 `outputs/`，不会提交到仓库。

solver 不负责判断最终答案是否正确。独立的等价性验证流程和输出格式见同目录的 `ANSWER_VERIFICATION.md`，从而保证生成证据、答案提取和评分可以分别升级及复查。
