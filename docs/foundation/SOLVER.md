# Hy3 Solver 设计与使用

## 目标

第一阶段 solver 负责从 benchmark 读取数学题，调用 Hy3 生成可见的分步解答，并将一次 inference 的请求、原始响应、解析结果、用量、时间和错误完整写入 JSONL。此阶段不进行答案评分或过程正确性评估。

## 架构

```text
data/benchmark/math_text.jsonl（默认纯文字候选池）
              |
              v
       Dataset Loader
       仅保留 id/dataset/problem
              |
              v
        Prompt Builder
      math-solver-v2
              |
              v
          Hy3 Client
 OpenAI-compatible SSE stream
              |
              v
    Stream Chunks + 聚合响应
              |
              +------------------+
              |                  |
              v                  v
      Response Parser      原始chunks完整保存
              |                  |
              +--------+---------+
                       v
       outputs/solver_outputs.jsonl
```

模块职责：

- `solver/dataset.py`：只生成 `SolverSample(id, dataset, problem)`，从类型边界上阻止参考答案、参考解答和 metadata 进入模型请求。
- `solver/prompt.py`：集中维护 prompt 模板与版本号。
- `solver/client.py`：独立封装 Hy3 API 鉴权、流式接收、chunk聚合和完整响应读取，不包含 benchmark 逻辑。
- `solver/parser.py`：从可见回答中提取编号步骤和候选最终答案；不修改原始响应。
- `solver/runner.py`：负责样本选择、断点续跑、重试、计时和逐条追加 JSONL。

## Solver Prompt

`math-solver-v2`面向后续过程评估，要求每个Step承担一个连贯数学阶段、给出后续会使用的关键中间依据、在必要时显式处理定理条件和case，并固定以`Final Answer: \boxed{...}`结尾。它不要求每步是单一原子操作，也不要求输出步骤类型或依赖字段。

v2要求可见`response.content`尽量提供以下数学信息：

- 连续编号的解题阶段，以及该阶段正在完成的数学目标；
- 后续步骤实际使用的关键中间结果、计算或推导依据；
- 必要的定理、恒等式和题目条件，以及它们被使用的位置；
- 可能增根、漏解或失效时所需的定义域、符号、边界和候选解检查；
- 必要的case划分、组合或排除；
- 一条主要解法和一个显式最终答案。

这些信息描述的是Solver愿意公开并用于支持结论的“可见解答”，不是模型内部思考的逐字转录。Process Evaluator判断的对象正是这份可见数学证据；如果关键依据没有写入`response.content`，即使模型可能在内部考虑过，也应按可见证据不足处理。

当前 Prompt 有两个刻意保留的边界。第一，一个Step可以包含一小段连续推导，所以首错只能定位到`Step N`，不能保证定位到步骤内部的某个子推断。第二，Solver不输出`type`、`depends_on`、置信度或参考解答对齐字段；这些结构既不是数学正确性的真值，也不应由Solver自行宣称。

运行示例：

```bash
uv run python -m solver.runner \
  --id math-test-algebra-0024
```

Prompt 只包含题目与求解指令，不包含参考答案、参考解答或 benchmark metadata。Prompt v1/v2 的最终对照指标见 [`results/analysis_metrics.json`](../../results/analysis_metrics.json)。

runner 默认读取 `data/benchmark/math_text.jsonl` 的250道纯文字MATH题。原含图形子集的`math.jsonl`、GSM8K、AIME和400题合并数据仍保留，但只有显式传入相应`--input`时才使用；AIME当前暂停评测。

## API 配置

solver 使用腾讯云 TokenHub 的 OpenAI-compatible Chat Completions API。默认参数：

| 参数 | 默认值 |
| --- | --- |
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model | `hy3` |
| Temperature | `0.9` |
| Top P | `1.0` |
| Max output tokens | `32000` |
| Thinking | `enabled` |
| Reasoning effort | `high` |
| Stream | `true`，请求最终usage chunk |
| Timeout | `300s`网络读取超时 |
| Runner retries | `0` |

默认输出上限为32000 token，网络读取超时为300秒，且默认不自动重试。输出上限不保证所有样本完成，因此批量运行仍需检查 `finish_reason` 并单独处理截断结果。

客户端使用SSE流式接收，分别累积`delta.reasoning_content`和`delta.content`，并通过`stream_options.include_usage=true`获取最后一个usage chunk。流式传输不改变`max_tokens`或计费；300秒timeout约束连续网络读取等待，而不是整次推理的总墙钟时间。

每次调用的chunks同步追加到独立事件JSONL。`stream_started`表示请求开始，`stream_completed`只表示`finish_reason=stop`，`stream_incomplete`表示流正常结束但生成未完成，`stream_interrupted`表示异常中断。正式solver记录仍在完整聚合后一次性写入；事件文件只保留恢复和审计证据，不直接参与评分。

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
- 默认不自动重试；只有显式设置`--max-retries`才对请求异常重试，并记录每次错误。
- 正式记录分别保存`request_status`和`generation_status`。只有`finish_reason=stop`对应`generation_status=complete`。
- 默认resume会跳过已有成功请求，包括生成不完整的记录，避免相同参数反复调用。
- `--retry-incomplete`显式重跑请求成功但生成不完整的样本；`--no-resume`显式重复全部选中样本。两者不能同时使用。
- 流事件文件默认位于正式输出旁的`*_stream_events.jsonl`，也可用`--stream-events-output`指定。

## 输出记录

每行对应一次 inference，主要字段包括：

```text
schema_version
run_id / inference_id
status
request_status / generation_status
sample.id / sample.dataset / sample.problem
prompt.template_version / prompt.messages
request（不含 API Key）
timing.started_at / finished_at / latency_ms
attempt_count / attempt_errors
response.http_status / headers / provider_response_id
response.content / reasoning_content / usage / raw
parsed.parser_version / steps / final_answer / warnings
```

`response.raw` 保存客户端聚合后的完整响应及原始`stream_chunks`；`response.content`是模型正式给出的分步解答与最终答案，也是后续过程评估的唯一模型过程对象。内部`reasoning_content`单独保存，只用于本地诊断模型自身的思考、循环与截断，不等同于模型明确给出的解题步骤。运行输出位于被 Git 忽略的`outputs/`，不会提交到仓库。

因此，Solver记录足以复查一次生成的题目、prompt版本、可见解答、解析结果、完成状态、tokens、耗时和provider原始响应，也足以把后续答案验证与过程评估关联到唯一`inference_id`。它不能证明可见推导本身正确；这分别由独立答案验证、Process Evaluator及后续人工真值实验回答。

solver 不负责判断最终答案是否正确。独立的等价性验证流程和输出格式见同目录的 `ANSWER_VERIFICATION.md`，从而保证生成证据、答案提取和评分可以分别升级及复查。

独立过程评估流程见同目录的`PROCESS_EVALUATOR.md`。它只把`response.content`作为Solver的正式过程证据，不读取Solver内部`reasoning_content`。
