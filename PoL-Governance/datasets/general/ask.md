# 通用问题集批量作答（ask.py 操作手册）

给 [general 契约](CONTRACT.md) 的 `items.jsonl` 批量取外部答案（默认面向官方 Jev）。
**默认离线**：不加 `--live` 只写请求计划，不联网、不读密钥。密钥只从环境变量或 `--key-file` 读，
任何产物里都只有 sha256 前 8 位指纹。

一句话流程：`plan`（离线看清要问什么）→ `run --dry-run`（离线核对请求包）→
`run --live`（真跑，可随时中断和续跑）→ `verify`（按契约 2.2 核对）→ `report`（用量/失败统计）。

## 1. 你需要提供什么

| 需要 | 怎么给 | 说明 |
|---|---|---|
| Jev 完整地址 | `--endpoint https://...` | 官方文档给的 URL 原样粘贴；也可再拆 `--request-path` |
| 官方 api_version | `--api-version <版本>` | 写进 `source=jev-<版本>` 与文件名 |
| 密钥 | `$env:JEV_API_KEY = "<密钥>"` 或 `--key-file <credentials.yaml>` | `--key-file` 可直接指向 DSH credentials.yaml 的 `refs:` 段 |
| 协议已核对 | `--integration-confirmed` | 你按官方文档核对过请求/响应形状后加；缺这一项 `--live` 直接退出 2 |

四项缺任何一项都不会降级到别的答案源，而是**退出码 2 并说明缺什么**（离线预演只要求 endpoint + 版本）。

## 2. 命令

```powershell
cd <仓库根>

# (1) 离线：把 items.jsonl 展平成请求清单（qid/state/question/options），可直接交给 Jev
uv run --no-project --offline python datasets/general/ask.py plan `
  --items datasets/general/data/items.jsonl --out D:\pol2-out\requests.jsonl

# (2) 离线预演：写出真实请求包（URL/头/包体），核对形状；不联网
uv run --no-project --offline python datasets/general/ask.py run `
  --items datasets/general/data/items.jsonl --out D:\pol2-out --backend jev `
  --endpoint https://<官方地址>/<路径> --api-version <版本>

# (3) 先小样本再放量：--limit 200 / --keys action,harmful / --domains risk_harm 任选
#     --keys 取 items 里的 question key（键表见 db-schema 的 taxonomy.py QUESTION_KEYS）
uv run --no-project --offline python datasets/general/ask.py run `
  --items datasets/general/data/items.jsonl --out D:\pol2-out --backend jev --live `
  --endpoint https://<官方地址>/<路径> --api-version <版本> --integration-confirmed `
  --limit 200 --workers 4

# (4) 全量：一条命令跑完（把 $env:JEV_API_KEY 设好）
$env:JEV_API_KEY = "<密钥>"
uv run --no-project --offline python datasets/general/ask.py run `
  --items datasets/general/data/items.jsonl --out D:\pol2-out --backend jev --live `
  --endpoint https://<官方地址>/<路径> --api-version <版本> --integration-confirmed `
  --workers 8

# (5) 断了/想继续：把命令 (4) 原样再跑一遍即可（已 ok 的自动跳过、失败项不重跑）
#     只想把失败项重跑一遍：命令 (4) 末尾加 --retry-failed

# (6) 核对与统计
uv run --no-project --offline python datasets/general/ask.py verify `
  --items datasets/general/data/items.jsonl --answers D:\pol2-out\answers.jev-<版本>.jsonl
uv run --no-project --offline python datasets/general/ask.py report `
  --calls D:\pol2-out\calls.jev-<版本>.jsonl --answers D:\pol2-out\answers.jev-<版本>.jsonl `
  --items datasets/general/data/items.jsonl
```

产物目录自定（上例 `D:\pol2-out`）；若放进仓库，注意 [README](CONTRACT.md) 第 5 节把 `data/` 归 Lead 统管。
`--out` 给目录就写 `<目录>/answers.<source>.jsonl`，给 `.jsonl` 文件路径则按该路径写。

## 3. 产物

| 文件 | 内容 | 用途 |
|---|---|---|
| `answers.<source>.jsonl` | **交付物**，契约 2.2 的 11 个字段，一 qid 一行，按 items 顺序 | 交叉优化/训练 |
| `journal.<source>.jsonl` | 与 answers 同字段的追加日志，每完成一条立即 flush | **断点续跑**的真实来源 |
| `calls.<source>.jsonl` | 每次 HTTP 尝试 + 每个 qid 的判定结果（无密钥本体） | 成本、限速、**失败原因** |
| `requests.<source>.jsonl` | 离线请求计划（URL/头/包体或 fixture 规则） | 交给 Jev 或人工核对 |

`--source` 默认 `jev-<api-version>`，直接写进文件名与 `source` 字段。

## 4. 续跑与失败语义

- **已 ok 的 qid 默认跳过**；重跑同一条命令即可续跑，速度是 O(已答) 的读文件时间。
- **失败项默认也跳过**（不会被悄悄改成 ok）；加 `--retry-failed` 才重跑 `timeout/error/invalid`。
- 每条答案一落定就写 journal 并 flush，**Ctrl+C 只等已在飞的请求**，然后压缩落盘 → 直接重跑续上。
- 最终文件按 items 顺序原子重写，**一个 qid 只有一行**（重试会覆盖旧行）。
- 退出码：`0` 选中范围全部 ok；`1` 仍有非 ok（提示加 `--retry-failed`）；`2` 配置/契约错误。

## 5. 看失败原因 / 核对结果

```powershell
# 失败分类、延迟、token、成本、失败 qid 与原因（前 20 条）
python datasets/general/ask.py report --calls <calls.jsonl> --answers <answers.jsonl> --items <items.jsonl>
# 机器可读：加 --json
# 逐条原因在 calls.jsonl 里：phase=outcome 的 execution_status / failure_reason，
# phase=attempt 的 status_code / failure_kind / error（timeout / error / invalid）。
```

`verify` 按契约 2.2 逐行校验（字段、qid=<item id>.<key>、取值域、概率归一、分数范围）并给出覆盖缺口：
退出 `0`=全部 ok 且无违约；`1`=格式合法但缺答/有失败（`--allow-incomplete` 可当成 0）；`2`=契约违约。

## 6. Jev 适配层：已实现与待确认

已实现（截至官方接口未核实，按 [pipeline/jev.py](../pol2/pipeline/jev.py) 的既有假设）：

```jsonc
// POST <endpoint><request-path>   Authorization: Bearer <JEV_API_KEY>
{"api_version": "<版本>",
 "requests": [
   {"qid": "<item id>.action_selection", "kind": "choice", "state": "...", "question": "...",
    "options": [{"key": "allow", "label": "放行"}, {"key": "repair", "label": "修正后复查"}]},
   {"qid": "<item id>.harm_severity", "kind": "score", "state": "...", "question": "...",
    "scale": {"min": 0, "max": 4, "labels": ["无伤害", "轻微", "中等", "严重", "灾难性"]}}]}
// 接受的响应：{"answers": {"<qid>": {"answer": ..., "probs": {...}}}} 或
//            {"answers": [{"qid": ..., "answer": ...}, ...]}；单问模式也接受裸 {"answer": ...}
```

请求包里的 `options` / `scale` 原样取自 items.jsonl；题型由 [taxonomy.py](taxonomy.py) 的
`validate_question` **唯一裁定**（score 的 `labels` 是 `min..max` 的**字符串数组**，长度 = max-min+1；
choice/noul 只有 `options`）。plan/run 默认还会用 `taxonomy.item_errors` 做 README 2.1 全条目校验，
形状不对在花钱之前就退出 2（确需绕过用 `--skip-item-schema`）；report/verify 只校验被消费的字段。

拿到官方文档后需要确认的参数（都用开关适配，不必改代码）：

| 文档里要确认的点 | 现在的默认 | 开关 |
|---|---|---|
| 完整 URL 是否含路径 | `--endpoint` 原样使用 | `--endpoint`、`--request-path` |
| api_version 放请求体还是请求头 | 请求体 `api_version` | `--version-in header` / `--version-header` |
| 鉴权头 | `Authorization: Bearer <key>` | `--auth-scheme bearer\|api-key\|none`、`--auth-header`、`--extra-header NAME=VALUE` |
| 是否一次可问多条 | 每次 1 条 | `--batch-size N`（批内缺 qid 记 invalid） |
| 限速/配额 | 不限速 | `--rps`、`--workers`、`--max-attempts`、`--backoff` |
| 价格（可选） | 不计算成本（写 null，不编造） | `--price-in/--price-out`（每百万 token） |
| 请求体字段名（`requests[].question/state/kind/options/scale`） | 如上 | 若官方字段名不同，改 `JevBackend.envelope()`（唯一需要动代码的点） |
| 是否其实是 chat 接口 | — | `--backend openai-compatible --base-url <...>/v1 --model <...> --source jev-<版本>` |

## 7. 边界

- 官方请求/响应形状未核实前，`--live` 必须显式给 `--integration-confirmed`；不对就报错，不猜。
- 概率：源给了才写，键必须落在问题的取值域内（choice/noul 是选项 key；score 是 `"0".."max"` 的整数分级字符串）
  并归一到 1；只给部分取值也接受（calls 里标 `probs_partial`），越界键则整份丢弃（标 `probs_dropped`）。
  只给分布时 `answer` 取众数（标 `answer_from_probs`，平票取较小分级/靠前选项）；源没给概率时绝不编造。
- 失败永远不写 ok：`answer=null`、无 `probs`，只保留 `execution_status/latency_ms/created_at`。
- `--backend fixture` 是离线确定性合成答案（测试/演练用），**不是真值**，`source` 只能是 `fixture*`。
- 不写 private_holdout 相关任何内容；不提交密钥；`--save-raw` 之类不存在，原始响应不落盘。

## 8. 自测

```powershell
uv run --no-project --offline python -m unittest discover -s datasets/general -p "test_*.py" -q
```

其中 `fixtures/ask-items-sample.jsonl` 是从**真实 items.jsonl 截取的 10 条回归样本**
（覆盖 noul/choice/score、含与不含 targets、含 `next_step_candidate` 的条目自带选项、含 4 问条目），
测试直接读它，防止手搓 fixture 与转换器实际输出漂移。
