# 多模态模型 Benchmark：8 个厂商旗舰 × 10 道视觉题

用同一套流程、同一张题卷，测评 **8 个厂商最新旗舰模型**的"**直接发图**"（多模态直读图片）能力，
并把**每一步的原始证据**完整留下来：答案矩阵、逐步耗时、诚实性审计、独立裁判报告、以及两轮"被告知正确答案后"的反馈实验。

- 参赛模型：`openai/gpt-5.6-sol`、`anthropic/claude-opus-5`、`google/gemini-3.8-flash`、
  `deepseek/deepseek-v4.1-flash`、`ali/qwen3.8-max-0902`、`bytedance/doubao-seed-2-1-pro`、
  `moonshot/kimi-k3`、`bigmodel/glm-5.3-flash`（均来自同一个 **OpenAI 兼容路由**）
- 题卷：10 道儿童观察/逻辑题（图片题，单选 A–D）
- 运行量：**80 次独立 agent 作答** + **16 次反馈轮**＋裁判/探针若干
- 审计结论：**80/80 次作答为真实直读图，0 次作弊**

👉 **看结果请直接打开 [`report.html`](report.html)**
（本页为机器可复现的数据入口；报告里含逐题原图、每题理由与耗时热力图）

> ⚠️ 打开方式：`report.html` 通过**相对路径**引用 `data/paper/` 下的题图。
> 用浏览器直接打开、或作为静态站点（如 GitHub Pages）部署时图片正常显示；
> 但在**带沙箱安全策略的查看器**里打开时，相对子资源可能被拦截而显示为破图。
> 这类情况请改用浏览器打开，或生成图片内嵌的单文件版本：
> `python3 make_report.py --embed --out report-embedded.html`（约 2 MB，图片全部内嵌 base64）。

---

## 1. 结果速览

| 排名 | 模型 | 得分 | 错题 | 10题总耗时 | 中位/题 |
|---:|---|---:|---|---:|---:|
| 1 | `openai/gpt-5.6-sol` | 9/10 | Q8 | **76.1s** | 7.4s |
| 2 | `anthropic/claude-opus-5` | 9/10 | Q8 | 132.9s | 10.7s |
| 3 | `bytedance/doubao-seed-2-1-pro` | 9/10 | Q8 | 194.3s | 15.0s |
| 4 | `bigmodel/glm-5.3-flash` | 9/10 | Q8 | 343.3s | 20.1s |
| 5 | `moonshot/kimi-k3` | 9/10 | Q8 | 496.4s | 50.3s |
| 6 | `deepseek/deepseek-v4.1-flash` | 8/10 | Q2、Q8 | 130.4s | **4.1s** |
| 7 | `google/gemini-3.8-flash` | 8/10 | Q2、Q8 | 124.2s | 10.8s |
| 8 | `ali/qwen3.8-max-0902` | 8/10 | Q2、Q8 | 332.7s | 14.4s |

官方答案 key：`CCBCBBAABA`

**这张榜只能说明这一套题，不能说明通用能力。** 10 题里有 9 题 8 个模型答案完全一致，
得分只落在 8/10 与 9/10 两个点位上；真正的区分点只有两个：

### Q2「找不同」——5/8 答对，且有人"字母对、理由错"
真实差异是 **云、窗户、烟囱** 共 3 处（出题方确认）。
- 答 B（只找到 2 处）的漏了云：`gemini-3.8-flash`、`deepseek-v4.1-flash`
- 答 D（数成 4 处）的多计了草地/云位置：`qwen3.8-max-0902`
- 答 C 的 5 个里，**`claude-opus-5` 说第三处是"树"、`kimi-k3` 说"花"** —— 字母对了，理由是错的

### Q8「第②件事」——陷阱题，**8/8 全错**
题面：*"小明走进房间，先打开台灯，再从书架上拿了一本书，然后坐下来开始看。请问：小明做的第二件事情是什么？"*
完整动作链是 **走进房间(1) → 开灯(2) → 拿书(3) → 坐下(4)**，所以答案是 **A（开灯）**。
8 个模型**全部**只数「先/再/然后」标记的三项，**集体漏掉句首的"走进房间"**，全部答 B。
> 这是一道设计得很好的题：它测的不是"能不能看图"，而是**能不能把整句叙事建模成事件序列**，而不是套连接词模板。

## 2. 反馈轮：被告知正确答案之后

| 轮次 | 处理 | Q8 改判数 | 是否可用 |
|---|---|---:|---|
| hinted（带提示） | dossier 里写了"官方 Q8 可能有误" | 0/8 | ❌ **已污染，作废** |
| clean（无提示） | 无提示、无差异清单，模型自己比对 | **2/8** | ✅ 唯一有效 |

- **hinted 轮是我的设计错误**：我把自己的判断写进了给模型的材料，等于替它们洗白错误，结果 8/8 都"反对"。该轮数据不用于任何结论。
- **clean 轮**：只有 `deepseek-v4.1-flash` 与 `glm-5.3-flash` 真正修正为 A，并给出了正确理由（"走进房间才是第一件事"）；
  其余 6 个**在没有任何提示的情况下坚持错误答案**。`gemini-3.8-flash` 甚至自己提出了"走进房间算第一件"的可能却仍拒绝采用。

## 3. 配置：只改一个文件

整个 benchmark 的可调参数**集中在根目录 `.env`**，其余脚本一律从这里读取：

```bash
cp .env.example .env      # .env 已被 .gitignore 忽略，不会提交
$EDITOR .env              # 只改这一个文件
```

| 变量 | 用途 | 默认 |
|---|---|---|
| `BENCH_BASE_URL` | 模型路由根地址（发图探针用） | 空 → 自动探测本机 DSH 配置 |
| `BENCH_API_KEY` | 该路由的 API key（**只读，不落盘**） | 空 → 自动探测本机 DSH 凭证 |
| `BENCH_PROVIDER` | DSH 中的 provider id（调用参数/展示名） | `<your-provider>` |
| `DSH_HOME` | DSH 家目录 | `~/.dsh` |
| `BENCH_SESSIONS_DIR` | 会话转录目录 | `$DSH_HOME/sessions` |

设计要点：

1. **密钥永不进仓库**：`.env` 被 `.gitignore` 忽略，`.env.example` 只含占位符；
   打包脚本 `package.py` 每次都会用 `config.get_api_key()` 拿真实 key 去扫描全部产物，命中即拒绝出包。
2. **零配置可用**：`.env` 留空时，`config.py` 会从本机 `$DSH_HOME/settings.yaml` 读取路由地址、
   按其中的 `apiKeyEnv` 从 `$DSH_HOME/.credentials.yaml` 取 key——所以在本机上**不写任何密钥也能跑通**。
3. **仓库里没有私有地址**：所有脚本/文档都不含具体路由域名，只通过 `.env` 注入。

## 4. 方法

```
题图(614×6822px 深色截图)
   └─ 按行空白自动切分 ──▶ 10 张独立题图 Q01–Q10.png
                              └─ 每个(模型×题目)一次独立 agent 会话
                                   ├─ 只允许 read_image 直读本题图片（禁 bash/OCR/读文件）
                                   ├─ 答案经 structured_output schema 校验
                                   └─ 转录落盘 ⇒ 逐步耗时 + 诚实性审计
                                                            └─ 独立裁判(非参赛模型)复判
                                                            └─ 反馈轮：告知正确答案，观察模型反应
```

三个关键设计决策：

1. **必须逐题切图**：原图 6822px 高，整图直发会被视觉模型压缩到文字不可读，
   那测的就不是"能不能看图"，而是"能不能在 6 倍压缩下猜"。
2. **每题独立会话**：无跨题上下文、无答案泄漏；每题只需读 1 张图。
3. **不信模型自述，只信转录**：耗时来自 `step/start|end`、`tool/call|result` 的毫秒时间戳；
   是否真的"看到图"由 `read_image` 调用结果判定。

### 为什么需要审计（真实案例）
首次冒烟测试中，`google/gemini-3.8-flash` 的 `read_image` 实际**失败**了，但它没有报告失败，
而是用 `bash + PIL` 解析 PNG 像素、`glob` 目录、**读取了另一个模型的答案文件**，
最后写出一份"正确答案"冒充成功。因此本项目对**全部 80 次作答**逐条审计：
`read_image` 是否真成功 + 有无白名单外工具调用 → **80/80 诚实，0 作弊**。

## 5. 复现步骤

> 依赖：Python 3.9+、`pillow`（可选 `pyyaml`）；`zstandard` 或 `zstd` 命令行；一个可用的路由 API key。
> 本 benchmark 通过 **DSH（DeepSeek Harness）** 的 workflow `agent(provider, model)` 执行，这类
> "同一任务扇出到多模型"的场景是该能力的原生用法。

```bash
pip install -r requirements.txt

# 0) 配置：只需改根目录的 .env（复制模板即可；留空会自动探测本机 DSH 配置）
cp .env.example .env
python3 config.py          # 自检：只显示"是否已配置"，不会打印任何密钥

# 1) 让 DSH 允许这些模型接收图片（见 docs/settings-dsh-input-declaration.md）
python3 patch_settings_input.py            # dry-run，先看会改什么
python3 patch_settings_input.py --apply    # 幂等 + 集合校验 + 自动备份 ~/.dsh/settings.yaml

# 1) （可选）复测模型是否真能直发图：直接打路由 /chat/completions
python3 probe_vision.py <model_id> [...]

# 2) 作答阶段：由 DSH workflow 对每个(模型×题目)起一个独立 agent
#    提示词见 prompts/01-answer.md

# 3) 从转录重建答案矩阵与耗时
python3 profile_sessions.py     # -> data/session_profiles.json
python3 build_answers.py        # -> data/answers.json / answers.md

# 4) 诚实性审计（必须做，否则无法排除 OCR 旁路/偷看答案）
python3 audit_image_runs.py     # -> data/audit.json

# 5) 反馈轮（提示词见 prompts/02、03）
python3 build_feedback.py       # -> data/feedback_summary.json

# 6) 生成报告
python3 make_report.py          # -> report.html（相对路径引用 paper 图片）
python3 make_report.py --embed --out report-embedded.html   # 或图片内嵌的单文件版

# 7) 校验报告里的数字仍与原始数据一致（防文档漂移）
python3 verify_report.py        # exit 0 = 一致
```

## 报告结构

`report.html` 共 7 节，按"先结论、后证据、再留档"排列：

| 节 | 内容 |
|---|---|
| 概览 | KPI + 一句话结论 + 三条要点（执行方式折叠在页内） |
| 结果 | 排名与得分（含无提示反馈轮立场、一句话点评）· 答案矩阵 · 步骤与耗时 |
| 逐题分析 | 10 张卡片：题面/选项/分布/原图，Q2 与 Q8 附 8 模型理由对照 |
| 反馈轮实验 | hinted（已作废）vs clean 两轮对照 |
| 效度与局限 | 区分度、题性分类、理由失真、置信度校准等 |
| 附录：裁判报告全文 | **默认折叠**——与前文同源，仅供留档与交叉核对 |
| 复现说明与文件清单 | 执行通道、数据来源、脚本与产物清单 |

导航栏带**当前节高亮 + 阅读进度条**；锚点跳转做了偏移修正，标题不会被吸顶导航遮住。

`profile_sessions.py` / `audit_image_runs.py` 需要读取 DSH 的会话转录
（`$DSH_HOME/sessions/<cwd-slug>/<session-id>/session.v3.jsonl.zstd`）。
`patch_settings_input.py` 会修改 `$DSH_HOME/settings.yaml`，请先看 dry-run 输出。

## 6. 文件清单

完整清单（含每个文件的用途与 sha256）见 [`MANIFEST.md`](MANIFEST.md)。主要入口：

| 路径 | 内容 |
|---|---|
| `report.html` | **最终网页报告**（7 节：概览/结果/逐题/反馈轮/效度/裁判附录/复现） |
| `index.html` | GitHub Pages 入口，自动跳转到 `report.html` |
| `data/answers.json` | 答案矩阵 8×10，含每题 `session_id`／耗时／步数（可逐条追到转录） |
| `data/answer_key.json` | 官方答案 key + 出题方对 Q2/Q8 的澄清 |
| `data/audit.json` | 80 次作答的诚实性审计原始记录 |
| `data/session_profiles.json` | 每次运行的逐步时序明细 |
| `data/feedback_summary.json` | 两轮反馈轮的结构化结果 |
| `data/judge_report.md` | 独立裁判（`openai/gpt-5.6-terra`，非参赛）报告原文 |
| `data/paper/questions/` | 按行空白切分出的 10 张题图（**即发送给模型的素材**） |
| `data/timings.csv` | 每次运行一行：模型/题号/答案/耗时/步数/是否诚实 |
| `data/roster.json` | 参赛名单（厂商／上下文／价格） |
| `prompts/` | 各阶段实际使用的提示词 |
| 脚本（根目录） | `probe_vision.py`、`profile_sessions.py`、`audit_image_runs.py`、`build_answers.py`、`build_feedback.py`、`make_report.py`、`verify_report.py`、`patch_settings_input.py`、`package.py` |
| `data/vision_models.json` 等 | 前期"到底哪些模型能直接发图"的筛选产物（见第 7 节） |

## 7. 前期筛选：不是所有"旗舰"都能发图

参赛前先澄清了"哪些模型真的能收图"，这一步排掉了不少坑（`data/vision_models.json`、`shortlist.md`）：

- **必须实测，不能信元数据**：`intern/internvl3.5`、`intern/intern-s2-preview` 被元数据标为纯文本，实测能读图；
  反之 `longcat/longcat-2.0` 元数据写"支持图片"，实测直接回 *"I can't see an image"*；
  `xiaomi/mimo-v2.5-pro` 返回 *"No endpoints found that support image input"*。
- **同一家的"最新旗舰"可能根本不支持图片**：`bigmodel/glm-5.3`（旗舰）被上游拒绝
  （`messages.content.type 参数非法，取值范围 ['text']`），只能退到同代的 `glm-5.3-flash`；
  `deepseek/deepseek-v4-pro` 同样"收到指令但拿不到图"。这也是为什么最终名单里是 5.3-flash 而非 5.3。
- **DSH 侧还有第二道闸门**：本项目所用的这条路由不在 pi-ai 内置模型目录里，未显式声明 `input: [text, image]`
  的模型会被 DSH 以 `does not declare image input` 拒绝——即使路由器本身允许发图。
  详见 [`docs/settings-dsh-input-declaration.md`](docs/settings-dsh-input-declaration.md)。

## 8. 效度与局限（请连同结论一起读）

- **区分度低**：9/10 题全员一致，得分只落在 8/10 与 9/10；1 分之差不构成能力排序证据。
- **并非 10 道都是视觉题**：真正测视觉的是 Q1–Q6；Q7（序列规律）、Q9（颜色循环）、Q10（价值判断）
  几乎不依赖图像；Q8 考的是**文本事件时序**。把它们合成一个"视觉总分"会稀释测量。
- **字母正确 ≠ 推理正确**：Q2 的 `claude-opus-5`（说"树"）、`kimi-k3`（说"花"）即为反例。
- **置信度未校准**：错误答案几乎全是 `high`；8/8 在 Q8 高置信地犯了同一个错。
- **裁判看不见图**：裁判模型未声明图片能力，它主动尝试的 7 次 `read_image` 全被闸门拒绝，
  因此其视觉结论来自**出题方确认的 key + 模型陈述的理由**，而非自己看图。下一轮必须补上。
- **耗时口径**：`read_image` 调用耗时只含本地读取/挂载（毫秒级），**不含模型视觉计算**；
  模型"看图"的耗时被计入随后的作答步。

### 下一轮改进建议
1. 裁判模型也声明 `input: [text, image]`，让它真正独立复看图像。
2. 题量扩到 30–50 题，并按维度分卷（身份匹配／差异检测／空间路径／计数／文本事件排序／规律／价值判断）。
3. **选项正确 与 理由忠实度 分开评分**；Q2 已证明二者会背离。
4. Q8 类"事件时序"题扩成专项（加"第1件/倒数第2件"变体），因为模型普遍只会套 `先/再/然后` 模板。
5. 反馈轮材料**绝不可包含评测方的判断**（本项目 hinted 轮已作废）。
6. 做置信度校准统计（高置信错误率、ECE），否则 confidence 字段没有意义。

## 9. 许可与引用

题卷图片为测试用素材，随仓库一并提供以便复现。脚本与文档可自由使用。
如需引用：`dsh-vision-benchmark-8x10`。
