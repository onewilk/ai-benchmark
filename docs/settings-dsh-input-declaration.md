# 为什么必须改 `settings.yaml`：DSH 的图片输入闸门

## 现象

DSH 的 `read_image` 工具会先校验**当前模型是否"声明"了图片输入**：

```js
// dsh-tool-fs: assertImageCapableRoute()
const active = await llm.resolveModelInfo(provider, model, signal);
if (active.inputModalities === undefined || !active.inputModalities.includes("image"))
  throw new Error(`cannot read "${path}" as an image: model "${model}" does not declare image input`);
```

`inputModalities` 来自 pi-ai 内置模型目录（`@earendil-works/pi-ai` 的 `getBuiltinModels`）。
**本项目使用的这条 route 不在该目录里**，因此该 route 上的每个模型都会回退到
`defaultInput`（仅 `text`）——**即使路由器本身完全允许发图**，`read_image` 照样被拒。
换句话说，这里的失败与"模型到底能不能读图"无关，**纯粹是宿主侧的声明缺失**。

实测证据（13 个候选、同一 route、未做任何声明时的闸门复验，原始回包见 `evidence/gate/`）：

| 模型 | 未声明时 `read_image` | 显式声明后 | 直连 API 发图 |
|---|---|---|---|
| `moonshot/kimi-k3`、`ali/qwen3.8-max-0902`、`bytedance/doubao-seed-2-1-pro`、`bigmodel/glm-5v-turbo`、`intern/intern-s2-preview`、`agnes/agnes-2.5-flash` | ❌ `does not declare image input` | ✅ 通过 | ✅ 能正确读图 |
| `anthropic/claude-opus-5`、`google/gemini-3.8-flash` | ❌ 同样被拒 | ✅ 通过 | ✅ 能正确读图 |
| `x-ai/grok-4.6` | ❌ 被拒 | （退出名单，未声明） | ✅ 能正确读图 |

**结论：这条 route 上没有任何"目录兜底"，凡未显式声明的模型一律被拒。**

> ⚠️ 一个踩过的坑：离线查询 pi-ai 内置目录（`getBuiltinModels()` 聚合 openrouter / vercel 等 provider）
> **能**查到 `anthropic/claude-opus-5`、`google/gemini-3.8-flash` 等同 id 记录且带 `text+image`，
> 但在该 route 上**并不生效**——它们照样被闸门拒绝。
> 因此判断依据必须是**通过该 route 实测 `read_image`**，而不是离线查目录。
> （这些目录记录只对 pi-ai 自己 ship 的 provider id 生效。）

## 解决：在模型条目上显式声明

`dsh-llm-pi-ai` 的模型条目 schema 支持 `input` 字段，且**优先于**目录：

```js
input: declaredInput(entry.input) ?? base?.input ?? [...request.defaultInput]
```

于是在 `$DSH_HOME/settings.yaml` 的对应模型条目上加一行即可：

```yaml
llm-pi-ai:
  providers:
    <provider-id>:            # 你的路由 provider
      models:
        - id: moonshot/kimi-k3
          name: Kimi K3
          contextWindow: 1000000
          maxTokens: 384000
          input: [text, image]      # ← 新增；可被 DSH 实时热加载
```

本项目用脚本完成（幂等、集合校验、自动备份）：

```bash
python3 patch_settings_input.py            # dry-run
python3 patch_settings_input.py --apply    # 写入，备份为 settings.yaml.bak-benchmark-<ts>
python3 patch_settings_input.py --prune --apply   # 反向：移除不在名单内的声明
```

脚本只在**名单内模型**上做增删，并在写盘前校验"声明集合 == 目标集合"，否则拒绝写入。

## 注意

- 声明的是**事实**：本项目只为**直连 API 实测能读图**的模型声明（见 `probes/probe_results.json`、
  `data/vision_models.json`）。不要给纯文本模型声明 image——那只会把失败推迟到请求阶段。
- 这是**宿主机全局配置**修改，会影响该机器上所有 DSH 会话；因此脚本带备份与集合校验。
- 验证是否生效：让该模型跑一次 `read_image`（本项目用 `final-gate` 检查），
  或直接查 pi-ai 目录 `getBuiltinModels()` 是否包含该 id。
