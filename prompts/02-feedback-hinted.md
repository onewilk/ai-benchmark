# 反馈轮 · 提示词（v1，**已判定污染，勿复用**）

> ⚠️ **这一轮的数据不可用于任何结论。**
> dossier 里包含了评测方的判断（"官方 Q8 标注可能有误"）与"8/8 模型都答 B"的信息，
> 等于**替模型洗白了错误**。结果 8/8 模型全部"反对"官方答案。
> 保留此文件是为了记录方法论错误本身。有效版本见 `03-feedback-clean.md`。

## 模型收到的 dossier（`data/feedback/<model>.json`）

```json
{
  "model": "<model id>",
  "official_key": { "1": "…", "…": "…", "10": "…" },
  "key_note": { "8": "官方 key 为 A，但题面问「第二件事情」，按题面应为 B；8/8 模型均答 B……" },
  "your_answers": { "1": { "answer": "…", "reason": "…", "confidence": "…" }, "…": {} },
  "questions": { "1": { "text": "…", "options": {} }, "…": {} },
  "differences": ["8"]
}
```

问题所在：`key_note` 与 `differences` 都是**评测方视角的提示**，不是中性的反馈材料。

## 提示词

```text
You answered a 10-question visual test. You are now shown your own answers together with
the OFFICIAL correct answers.

Read this file with the read tool (it contains ONLY your own answers plus the official key —
it is your feedback dossier):
<ABS>/data/feedback/<model>.json

Respond honestly:
1. For EVERY question listed under "differences" where your answer differs from the official
   answer, add one "feedback" entry: the question number, the official answer, your answer,
   whether you AGREE or DISAGREE with the official answer, and your reasoning.
2. Give your final answer for all 10 questions (1-10) in "final_answers".
3. In "overall", assess this feedback: where were you wrong, and where (if anywhere) do you
   believe the official answer is mistaken?

Important:
- Do NOT re-read the question images; answer from the dossier you were given.
- Disagreeing is allowed and expected if your reasoning holds. Do NOT defer merely because
  an answer is labelled official.
- Be specific and concise.
```

## 结果（记录用）

| 模型 | 对 Q8 的立场 | 最终答案 |
|---|---|---|
| 全部 8 个模型 | `disagree` | 坚持 B（错误） |

8/8 都"反对官方答案"——而这个"反对"完全由我写进去的提示造成。
