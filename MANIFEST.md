# MANIFEST

本目录由 `package.py` 生成：只收录本次 benchmark 的产物，并把 `audit.json` / `session_profiles.json` 收敛到本次的 96 个会话（80 次作答 + 16 次反馈），避免宿主机上无关会话内容被一并上传。

> 读 `audit.json` 时的口径：**80 次作答**全部通过「真实直读图」审计（`honest_direct_image_run: true`）；**16 次反馈轮**按设计只读取文本 dossier、不读图，因此它们的该字段为 `false` 属预期，不是作弊。每个会话都带 `benchmark_phase` 字段（`answer` / `feedback-hinted` / `feedback-clean`）。

| 文件 | 大小 | sha256（前 16 位） | 用途 |
|---|---:|---|---|
| `.env.example` | 1.2 KB | `4419f34ce58b4d1d` | 配置模板（复制为 .env；.env 已被 .gitignore 忽略） |
| `.gitignore` | 0.4 KB | `29f3763a9cc1521a` | 忽略凭证、缓存、可再生成的中间产物 |
| `README.md` | 14.6 KB | `1eb59927cf73912c` | 总入口：结果速览、方法、复现步骤、效度局限 |
| `_config.yml` | 0.3 KB | `87caac102141c971` | GitHub Pages/Jekyll 配置：强制包含 .env.example，避免站点上 404 |
| `audit_image_runs.py` | 6.3 KB | `1d9e38acecaea23f` | 诚实性审计：是否真 read_image、有无 OCR/偷看旁路 |
| `build_answers.py` | 3.2 KB | `190cb62e5c4fc4f1` | 从转录重建答案矩阵 |
| `build_feedback.py` | 3.6 KB | `34b9c2eabee93b93` | 从转录重建两轮反馈结果 |
| `config.py` | 5.3 KB | `2bfdbb924688d624` | 集中配置：读取根目录 .env，并可回退到本机 DSH 自动探测 |
| `data/all_model_ids.txt` | 4.6 KB | `2e30b22bf18efd6f` | 上者的模型 id 清单 |
| `data/all_models_raw.json` | 202.7 KB | `a603b05ce3b3f298` | 路由 /v1/models 原始元数据（205 个模型） |
| `data/answer_key.json` | 0.6 KB | `571e319e9a53b815` | 官方答案 key + 出题方对 Q2/Q8 的澄清 |
| `data/answers.json` | 31.1 KB | `91e1728efd16053c` | 答案矩阵 8×10，含每题 session_id/耗时/步数（可追到转录） |
| `data/answers.md` | 0.8 KB | `99d5fdf0f3ac2a96` | 答案矩阵 Markdown 版 |
| `data/answers_preview.md` | 18.3 KB | `5cd77ac65a023868` | 按题分组的 8 模型答案+理由对照（含分歧） |
| `data/audit.json` | 87.1 KB | `34ef5c41af0079c7` | 诚实性审计（已收敛到本次 96 个会话） |
| `data/feedback_summary.json` | 36.5 KB | `835f3bb510adc236` | 两轮反馈轮结构化结果（立场/是否改判/原文） |
| `data/judge_report.md` | 12.4 KB | `f0a2faf00d56cc62` | 独立裁判报告原文 |
| `data/paper/blocks.json` | 0.5 KB | `50b6af1693cc91e6` | 行空白切分得到的 10 个题目纵向边界 |
| `data/paper/questions/Q01.png` | 116.1 KB | `0eb0d04267ebf073` | 切分后的题图（发给模型的就是它） |
| `data/paper/questions/Q02.png` | 110.0 KB | `a4ae2491858d73e8` | 切分后的题图（发给模型的就是它） |
| `data/paper/questions/Q03.png` | 99.5 KB | `f9a6258ca1837197` | 切分后的题图（发给模型的就是它） |
| `data/paper/questions/Q04.png` | 100.3 KB | `7872a6fa31520588` | 切分后的题图（发给模型的就是它） |
| `data/paper/questions/Q05.png` | 210.5 KB | `2e7d3f258783e80b` | 切分后的题图（发给模型的就是它） |
| `data/paper/questions/Q06.png` | 89.0 KB | `55fa63eaff575468` | 切分后的题图（发给模型的就是它） |
| `data/paper/questions/Q07.png` | 50.8 KB | `61a706052df4a3b7` | 切分后的题图（发给模型的就是它） |
| `data/paper/questions/Q08.png` | 365.2 KB | `2c08f43d53924459` | 切分后的题图（发给模型的就是它） |
| `data/paper/questions/Q09.png` | 77.4 KB | `36c068f66849fe88` | 切分后的题图（发给模型的就是它） |
| `data/paper/questions/Q10.png` | 79.4 KB | `77f1e2c154fde78a` | 切分后的题图（发给模型的就是它） |
| `data/questions.json` | 3.8 KB | `9a9c620f4b41e7e7` | 题目文本/选项/是否有配图（转录，供报告与核对） |
| `data/roster.json` | 2.6 KB | `b2ffa80917383e96` | 参赛名单（厂商、上下文、价格、闸门验证状态） |
| `data/session_profiles.json` | 240.2 KB | `d4851b504d54ffda` | 逐步时序明细（已收敛到本次 96 个会话） |
| `data/shortlist.json` | 15.9 KB | `ad238ae5f8433b17` | 前期筛选：各厂商最新旗舰候选（含闸门/探针状态） |
| `data/timings.csv` | 9.5 KB | `0d06ae9495dd70ad` | 每次运行一行：模型/题号/答案/耗时/步数/是否诚实 |
| `data/vision_models.json` | 44.0 KB | `c6f02dba6ffe37d0` | 前期筛选：可发图模型清单（含探针实测结论） |
| `docs/settings-dsh-input-declaration.md` | 3.7 KB | `f2c101ce7de6d23f` | 为什么/如何为模型声明 input:[text,image]（DSH 图片闸门） |
| `evidence/gate/gate_agnes_agnes-2.5-flash.json` | 0.1 KB | `8bc26e49fe4d6824` | 闸门复验原始回包 |
| `evidence/gate/gate_ali_qwen3.8-max-0902.json` | 0.1 KB | `63132056f0faf3d9` | 闸门复验原始回包 |
| `evidence/gate/gate_anthropic_claude-opus-5.json` | 0.3 KB | `529d17edf51bf2aa` | 闸门复验原始回包 |
| `evidence/gate/gate_bigmodel_glm-5v-turbo.json` | 0.1 KB | `cb6120b1762cdfc3` | 闸门复验原始回包 |
| `evidence/gate/gate_bytedance_doubao-seed-2-1-pro.json` | 0.1 KB | `b742bb317873d087` | 闸门复验原始回包 |
| `evidence/gate/gate_deepseek_deepseek-v4.1-flash.json` | 0.1 KB | `dcc9a90ea0969ce6` | 闸门复验原始回包 |
| `evidence/gate/gate_google_gemini-3.8-flash.json` | 0.3 KB | `57a248bd46dd31dc` | 闸门复验原始回包 |
| `evidence/gate/gate_intern_intern-s2-preview.json` | 0.1 KB | `11b0c8159f110c36` | 闸门复验原始回包 |
| `evidence/gate/gate_moonshot_kimi-k3.json` | 0.1 KB | `e6c5925cfb57f77b` | 闸门复验原始回包 |
| `evidence/gate/gate_x-ai_grok-4.6.json` | 0.3 KB | `23d3c32bbd8f0c5c` | 闸门复验原始回包 |
| `generate_shortlist.py` | 15.3 KB | `c3f121b9c9255b32` | 生成前期候选清单（md/json/html） |
| `generate_vision_catalog.py` | 11.7 KB | `d1c517c89de14e55` | 生成可发图模型目录（需先跑探针） |
| `index.html` | 1.2 KB | `c6116e210f343662` | GitHub Pages 入口：自动跳转到 report.html |
| `make_report.py` | 37.7 KB | `b4f9a0285313e927` | 生成 report.html（--embed 出图片内嵌单文件版，--out 指定输出名） |
| `package.py` | 16.0 KB | `34e6b87f8c767a01` | 打包本导出目录（会话范围收敛 + 清单 + 安全校验） |
| `patch_settings_input.py` | 5.1 KB | `2c4c811ff99af5e6` | 为名单内模型声明 input:[text,image]（幂等/集合校验/备份） |
| `probe_vision.py` | 4.6 KB | `e9f14a27c2a0462b` | 直连 API 发图探针 |
| `probes/capability_test.png` | 2.0 KB | `cfed613f7f80fff4` | 探针图（红圆+绿方+CODE 7291） |
| `probes/probe_results.json` | 21.2 KB | `344769a871aa1b7c` | 直连 API 发图探针原始回包 |
| `profile_sessions.py` | 6.5 KB | `926ab92b54ce846f` | 从 DSH 会话转录提取逐步时序与答案 |
| `prompts/01-answer.md` | 2.1 KB | `b028fc6874234285` | 作答阶段提示词（逐题独立会话） |
| `prompts/02-feedback-hinted.md` | 2.2 KB | `3f0e1fe4ab6dcf11` | 反馈轮 v1（**已污染，作废**，保留以记录方法论错误） |
| `prompts/03-feedback-clean.md` | 2.9 KB | `aa51384255bd4c3a` | 反馈轮 v2（有效版本） |
| `prompts/04-judge.md` | 3.5 KB | `865be0ee1feaa491` | 独立裁判提示词（含其看不见图的局限披露） |
| `prompts/05-readiness.md` | 2.6 KB | `282ca1a85a16bd16` | 探针 / 闸门复验 / 题卷转录提示词 |
| `report.html` | 57.2 KB | `113f5ca23babfe21` | **最终网页报告**（逐题原图/答案矩阵/耗时热力图/折叠的裁判全文） |
| `requirements.txt` | 0.4 KB | `da180210a0af8f39` | Python 依赖 |
| `shortlist.html` | 20.0 KB | `8d5dbc68ffe677ac` | 候选清单交互筛选页 |
| `shortlist.md` | 4.2 KB | `31a998c501d50e38` | 候选清单 Markdown（含元数据误报案例） |
| `verify_report.py` | 4.8 KB | `e339f66d1e07054c` | 校验报告中的数字仍与原始数据一致（防文档漂移） |

合计 65 个文件，2.22 MB。
