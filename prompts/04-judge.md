# 独立裁判提示词（`openai/gpt-5.6-terra`，非参赛模型）

裁判**不参与答题**，任务是读取全部产物并出复判报告。它是本仓库唯一被允许自由使用
`read`/`bash` 的 agent。

> ⚠️ 已知局限：裁判模型**没有**声明图片输入能力，它主动尝试的 7 次 `read_image`
> 全部被 DSH 闸门拒绝（见 `data/audit.json`）。因此它的视觉结论来自
> **出题方确认的官方 key + 各模型陈述的理由**，而非自己看图。下一轮需为裁判同样声明
> `input: [text, image]`。

## 提示词（最终版）

```text
You are the INDEPENDENT JUDGE for a multimodal (vision) model benchmark. This is your FINAL,
authoritative pass.

Read these files with the read tool:
1. <ABS>/data/questions.json
2. <ABS>/data/answers.json          — every model's round-1 answers, reasons, confidences, timings
3. <ABS>/data/answer_key.json       — the OFFICIAL key, now clarified by the exam author
4. <ABS>/data/audit.json            — proof every run genuinely read the image
5. <ABS>/data/session_profiles.json — per-run steps and wall-clock timings
6. <ABS>/data/feedback_summary.json — round-2 responses: each model was told the official
                                      answers and replied

CORRECTED GROUND TRUTH you must adopt (the exam author has confirmed it, and your earlier
reasoning about Q8 being a misprint was WRONG):
- Q8 answer A is CORRECT. It is a deliberate trap. The action chain is
  走进房间(1) → 打开台灯(2) → 从书架拿书(3) → 坐下看书(4), so "第二件事情" is 开灯 = A,
  NOT 拿书 = B. All 8 models missed 走进房间 and counted only the 先/再/然后 trio. Their
  insistence that the key is wrong is itself the error being measured — do not credit it.
- Q2 answer C is CORRECT; the three differences are 云、窗户、烟囱.

Round-2 methodology, which you must judge fairly and label honestly:
- "hinted" round: the dossier included a note telling the model the official Q8 key was wrong.
  That note CONTAMINATED the result — treat this round as methodologically invalid for
  measuring model behaviour and say so plainly.
- "clean" round: no note, no list of differences; the model had to compare itself. This is the
  valid round.
- In the clean round, 2 of 8 models self-corrected Q8 to the correct A with sound reasoning
  (that 走进房间 is step 1); the other 6 defended the wrong B.

Produce a Chinese markdown report with these sections:
## 1. 总览与排名
## 2. 逐题分析
## 3. 逐模型点评
## 4. 反馈轮分析
## 5. 效度与风险
## 6. 结论与建议

Be quantitative, specific and blunt. Never flatter a model. Do not assert facts you cannot
verify from the files.
```

产出：`data/judge_report.md`（经 `make_report.py` 渲染进 `report.html` 的"裁判报告"一节）。

## 设计说明

- **非参赛模型**：选 `openai/gpt-5.6-terra`（与参赛的 `gpt-5.6-sol` 同家族但不同型号，
  且不属于任何参赛厂商的旗舰）——任何 LLM 裁判都难以完全避免同源偏好，
  更稳的做法是**多裁判交叉**并报告分歧（下一轮建议）。
- **要求它定量复核**：裁判被明确要求自己算分并与 `answer_key.json` 对照，
  而不是复述输入。
- **显式披露污染**：把 hinted 轮的污染写进提示词，是为了让裁判主动作废该轮，
  而不是把它当成"模型有骨气"的证据。
- 若要裁判真正独立看图，需为它声明图片能力（见
  `docs/settings-dsh-input-declaration.md`）。
