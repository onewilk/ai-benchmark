# 作答提示词（每个"模型 × 题目"起一个独立 agent）

这是**逐题独立会话**模式下实际使用的提示词模板。
关键约束：只许用 `read_image` 直读本题图片，禁止一切旁路；答案经 schema 校验返回。

## 模板

```text
You are taking a test. Answer exactly ONE question.

The question you must answer is shown in this image — read it with the read_image tool:
<ABS>/data/paper/questions/Q<NN>.png

STRICT RULES — violating any of them invalidates your run:
- Use ONLY the read_image tool. Do NOT use bash, glob, grep, read, write, or any other tool.
- Do NOT look for other files, answer keys, or other questions. This image IS your question.
- Do NOT use OCR or pixel analysis. Read the image with read_image and reason about what you see.

Study the image carefully, including any picture, then choose the correct option.

Give: answer ("A", "B", "C" or "D"), a one-sentence reason in Chinese, and your confidence.
```

## 结构化输出 schema

```json
{
  "type": "object",
  "properties": {
    "answer":     { "type": "string", "enum": ["A", "B", "C", "D"] },
    "reason":     { "type": "string" },
    "confidence": { "type": "string", "enum": ["high", "medium", "low"] }
  },
  "required": ["answer", "reason", "confidence"],
  "additionalProperties": false
}
```

## 调用方式（DSH workflow）

```js
const r = await agent(task(q), {
  label: `${model} Q${q}`,
  provider: "<your-provider>",
  model,                        // ← 每个模型一个独立 route
  phase: model,
  schema,
});
```

要点：

- **一个 (模型, 题目) 一个子会话**：无跨题上下文，也不会把别的模型的答案带进来。
- 禁止清单（`bash/glob/grep/read/write`）在事后由 `audit_image_runs.py` 从转录核验，
  违规会被标记为 `CHEATED/INVALID`。白名单：`read_image`、`structured_output`、`write`、`present`。
- `reason` 用于后续人工/裁判评估"理由是否忠实于图像"，
  因为**选项字母正确并不等于视觉推理正确**（见报告 Q2 中 `claude-opus-5`／`kimi-k3` 的反例）。
