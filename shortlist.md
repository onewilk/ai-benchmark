# 各厂商最新旗舰「可发图」模型候选清单

共 27 个候选（推荐 13 / 备选 14），其中 27 个已实测通过发图。

## 推荐：各厂商最新旗舰

| 厂商 | 模型 id | 输入模态 | 上下文 | 价格(进/出 CNY) | 发图实测 | 备注 |
|---|---|---|---|---|---|---|
| OpenAI | `openai/gpt-6-astra` | (元数据未标注) | 400K | 70/350 | ✅ 已读图 | GPT-6 旗舰，端到端 agent / 深度研究 |
| Anthropic | `anthropic/claude-opus-5` | text+image+file | 1.0M | 35/175 | ✅ 已读图 | Opus 5 旗舰，复杂推理+长期规划 |
| Google | `google/gemini-3.8-flash` | (元数据未标注) | 100K | 5.25/26.25 | ✅ 已读图 | Gemini 3.8 Flash，最新一代 |
| DeepSeek | `deepseek/deepseek-v4.1-flash` | (元数据未标注) | 1.0M | 1/4 | ✅ 已读图 | V4.1 Flash，最新视觉实验线 |
| 阿里 Qwen | `ali/qwen3.8-max-0902` | (元数据未标注) | 1.0M | 12/36 | ✅ 已读图 | Qwen3.8-Max 快照版，2.4T MoE 旗舰 |
| 字节豆包 | `bytedance/doubao-seed-2-1-pro` | text+image+video | 256K | 6/30 | ✅ 已读图 | Seed-2.1 Pro，Coding/Agent 旗舰 |
| 月之暗面 | `moonshot/kimi-k3` | text+image+video | 1.0M | 20/100 | ✅ 已读图 | Kimi K3，2.8T 参数旗舰 |
| xAI | `x-ai/grok-4.6` | text+image+file | 2.0M | 14/42 | ✅ 已读图 | Grok 4.6，最新旗舰（2M 上下文） |
| 智谱 GLM | `bigmodel/glm-5v-turbo` | text+video+image | 200K | 5/22 | ✅ 已读图 | GLM-5V-Turbo，多模态 Coding 基座 |
| MiniMax | `minimax/minimax-m3` | text+image+video | 1.0M | 2.1/8.4 | ✅ 已读图 | MiniMax M3 旗舰 |
| Intern | `intern/intern-s2-preview` | text | 128K | 0/0 | ✅ 已读图 | Intern-S2 Preview（元数据漏报，实测可发图） |
| Agnes | `agnes/agnes-2.5-flash` | (元数据未标注) | 512K | 0/0 | ✅ 已读图 | Agnes 2.5 Flash（元数据未标注） |
| Meta | `meta/llama-4-scout` | text+image | 128K | 0.56/2.1 | ✅ 已读图 | Llama 4 Scout（唯一在售 Meta 视觉模型） |

## 备选：同代其它型号

| 厂商 | 模型 id | 输入模态 | 上下文 | 价格(进/出 CNY) | 发图实测 | 备注 |
|---|---|---|---|---|---|---|
| OpenAI | `openai/gpt-5.6-sol` | text+image+file | 400K | 35/210 | ✅ 已读图 | GPT-5.6 系列旗舰（Sol 层） |
| OpenAI | `openai/gpt-5.6-terra` | text+image+file | 400K | 14/84 | ✅ 已读图 | GPT-5.6 均衡层（Terra） |
| Anthropic | `anthropic/claude-sonnet-5` | text+image+file | 1.0M | 14/70 | ✅ 已读图 | Sonnet 5，最新 Sonnet 级 |
| Anthropic | `anthropic/claude-fable-5.1` | (元数据未标注) | 1.0M | 70/350 | ✅ 已读图 | Fable 5.1，知识工作向 |
| Google | `google/gemini-3.7-flash` | (元数据未标注) | 100K | 5.25/26.25 | ✅ 已读图 | Gemini 3.7 Flash |
| Google | `google/gemini-3.6-flash` | text+file+audio+image+video | 1.0M | 10.5/52.5 | ✅ 已读图 | Gemini 3.6 Flash |
| DeepSeek | `deepseek/deepseek-v4-flash-vision-exp` | text+image | 1.0M | 1/4 | ✅ 已读图 | V4 Flash Vision Exp |
| 阿里 Qwen | `ali/qwen3.8-max` | text+image+video | 1.0M | 12/36 | ✅ 已读图 | Qwen3.8-Max 正式版 |
| 阿里 Qwen | `ali/qwen3.8-flash` | text+image+video | 1.0M | 1/3 | ✅ 已读图 | Qwen3.8-Flash 高性价比 |
| 阿里 Qwen | `ali/qwen3-vl-plus` | text+image | 262K | 1/10 | ✅ 已读图 | Qwen3-VL-Plus 视觉专精 |
| 字节豆包 | `bytedance/doubao-seed-2-1-turbo` | text+image+video | 256K | 3/15 | ✅ 已读图 | Seed-2.1 Turbo 均衡版 |
| 月之暗面 | `moonshot/kimi-k2.7-code` | text+image | 256K | 6.5/27 | ⚠️ 部分正确 | Kimi K2.7 Code |
| xAI | `x-ai/grok-4.5` | text+image+file | 2.0M | 14/42 | ✅ 已读图 | Grok 4.5 |
| Intern | `intern/internvl3.5` | text | 128K | 0/0 | ✅ 已读图 | InternVL3.5（元数据漏报，实测可发图） |

## 元数据误报（声称支持图片，实测不支持）

- `longcat/longcat-2.0` — 实测明确回复「I can't see an image」，元数据误报
- `xiaomi/mimo-v2.5-pro` — 接口 404：No endpoints found that support image input
- `stepfun/step-3.5-flash-2603` — 接口 400：模型不支持图片输入
- `baidu/ernie-4.5-turbo-vl-preview` — 接口 401：当前 key 无该模型访问权限
- `tencent/hy4-preview` — 两次发图均返回空响应，无法确认可用