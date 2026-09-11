# 前置阶段提示词：探针 / 闸门复验 / 题卷转录

这三个阶段不是答题本身，但决定了"哪些模型能参赛"和"题目文本是什么"。

## 0) 直连 API 发图探针（`probe_vision.py`）

绕过 DSH，直接打模型路由的 `/v1/chat/completions`，判断模型**本身**能否收图。
探针图：`probes/capability_test.png`（红圆 + 绿方 + 文字 `CODE 7291`）。

```text
Look at this image and reply with exactly two lines:
1) the numeric code shown
2) the colour of the circle
No extra words.
```

判定：正文含 `7291` 且含 `red` 记为通过。**只看能不能收到图**，不看答题质量。

> 踩过的坑：`openai/gpt-6-astra` 拒绝 `max_tokens`，必须改用 `max_completion_tokens`；
> 部分模型把内容放在 `reasoning_content`，需要回退读取；否则会把"调用参数不对"
> 误判成"不支持图片"。

## 1) DSH 闸门复验（`final-gate`）

在 DSH 内部确认该 route 真的能通过 `read_image` 的模型能力校验。

```text
Image-input verification for route <model>.

STRICT RULES — violating any of them invalidates the run:
- You may use ONLY the read_image tool. Do NOT use bash, glob, grep, read, or any other tool.
- Do NOT use OCR, Python, or pixel analysis. Do NOT look for answer files.
- If read_image fails, report the failure honestly.

Steps:
1. Call read_image on <ABS>/probes/capability_test.png
2. Reply with the 4-digit caption code, the circle colour, and the rectangle colour.
3. End your reply with exactly one line of JSON:
   {"model":"<model>","read_image":"pass"|"fail","code":"...","circle":"...","rect":"...","error":"..."}
```

## 2) 题卷转录（仅供报告展示与人工核对）

**发给答题 agent 的只有图片和题号，没有题目文本**——转录文本仅用于报告与核对，
避免"给文本就等于送分"。

```text
Transcribe a 10-question test paper for a benchmark record.

Read ALL of these images with the read_image tool (one call each, in order):
<Q01.png … Q10.png 的绝对路径>

STRICT RULES: use ONLY read_image. Do NOT use bash, glob, grep, read, write or any other tool.
Do NOT write any file. Transcribe exactly what is printed — do not answer the questions.

Return ONLY a JSON array, no prose, in this exact shape:
[{"q":1,"text":"<full question stem, verbatim>",
  "options":{"A":"<text>","B":"<text>","C":"<text>","D":"<text>"},
  "has_figure":true|false}, ...]

Keep Chinese exactly as printed. If a question has an embedded picture, still transcribe
whatever text it contains.
```

产出 `data/questions.json`（本项目另做了人工抽验：Q4 蓝方块数、Q8 题面重复均为原卷原样）。
