# 反馈轮 · 提示词（v2，**有效版本**）

与 v1 的唯一区别：**去掉一切评测方判断**。dossier 只含模型自己的答案 + 官方 key，
模型必须**自己比对**出差异（不再给它 `differences` 列表），也不知道有"异常题"。

## 模型收到的 dossier（`data/feedback_clean/<model>.json`）

```json
{
  "model": "<model id>",
  "official_key": { "1": "…", "…": "…", "10": "…" },
  "your_answers": { "1": { "answer": "…", "reason": "…", "confidence": "…" }, "…": {} },
  "questions": { "1": { "text": "…", "options": {} }, "…": {} }
}
```

> 刻意不包含：`key_note`（评测方判断）、`differences`（差异清单）。

## 提示词

```text
You answered a 10-question test. The official correct answers have now been released.

Your dossier (your own answers and the official key):
<ABS>/data/feedback_clean/<model>.json

Read that file with the read tool, then:

1. Compare your answers against the official key YOURSELF and list the question numbers where
   they differ, in "differing_questions".
2. For each differing question, add a "feedback" entry: question number, the official answer,
   your answer, whether you AGREE or DISAGREE with the official answer, and your reasoning.
3. Give your final answer for all 10 questions in "final_answers".
4. In "overall", summarise your self-assessment: which of your answers were wrong, and do you
   believe any official answer is itself incorrect?

Important:
- Do NOT re-read question images; work from the dossier.
- Agreeing or disagreeing is your call — argue from the question text and your own reasoning.
  Do not defer merely because an answer is labelled "official".
- Be specific and concise.
```

## 结果

对 Q8（官方答案 A，8/8 首轮都答 B）：

| 模型 | 立场 | 最终答案 | 判定 |
|---|---|---|---|
| `deepseek/deepseek-v4.1-flash` | agree | **A** | ✅ 真正修正，理由正确（"走进房间才是第一件事"） |
| `bigmodel/glm-5.3-flash` | agree | **A** | ✅ 真正修正，理由正确 |
| `openai/gpt-5.6-sol` | disagree | B | ❌ 坚持错误 |
| `anthropic/claude-opus-5` | disagree | B | ❌ 坚持错误 |
| `google/gemini-3.8-flash` | disagree | B | ❌ 自己提出了"走进房间算第一件"的可能却仍拒绝采用 |
| `bytedance/doubao-seed-2-1-pro` | disagree | B | ❌ 把前置动作降格为"场景铺垫" |
| `moonshot/kimi-k3` | disagree | B | ❌ 坚持错误 |
| `ali/qwen3.8-max-0902` | disagree | B | ❌ 坚持错误 |

**2/8 真正修正**；其余 6 个在没有提示的情况下继续坚持错误信念。

Q2（官方 C）：首轮答错的 `gemini-3.8-flash`、`deepseek-v4.1-flash`、`qwen3.8-max-0902` 三个都接受改判为 C。

## 注意

提示词里"Disagreeing is allowed and expected… do not defer"这句**可能略微鼓励了反对**，
属于下一轮需要中性的地方（更中性的做法：只请模型"回应这份反馈"，不暗示任何倾向）。
