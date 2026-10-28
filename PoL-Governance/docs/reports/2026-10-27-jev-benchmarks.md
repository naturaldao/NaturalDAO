# 调研报告：Jev 类公开评测/排行榜 + JevBench 可执行性（2026-10-27）

> **一句话**：JevBench（coherence，无 gold）是**可以完全离线本地跑**的公开基准（`pip install jevbench`，Apache-2.0，数据随包），
> Kev 的 `POST /v1/systemone` 与其 wire format **逐字段一致**，并且**已用真实 Kev 权重在 CPU 上端到端跑通**（`kev-0.8b`：`check` 2.7 s 通过，`examples` 50 关系 1 分 57 秒，overall 66.4）；
> 只要 GPU 静默时段结束，用"项目 venv + PYTHONPATH"零安装 serve Kev，再用 1,248 次请求即可拿到**与官方榜同口径**的 mini 分数。
> 最大阻塞不是技术，而是：①排行榜**没有公开提交入口**（只有作者邮箱）；②coherence 可被"均匀回答"刷到 89.4，必须与 accuracy 同读。

- 报告日期：2026-10-28（北京时间）｜所有外部数字的抓取时间：2026-10-28 00:30–01:10 CST
- 环境：Windows 主机 + WSL Ubuntu-24.04；GPU = AMD Radeon RX 7900 XT（ROCm，torch 2.9.1+rocm7.2.1）
- 本报告**未运行任何 GPU 计算**（静默时段 00:30–09:30）；CPU 实测数据标注为「实测」，其余耗时/显存为引用或估算。
- 未读取私有保留集；未修改既有代码；未 commit。

---

## 0. 结论摘要（TL;DR）

1. **JevBench 能跑，且不需要网络。** `jevbench==0.1.0`（PyPI，Apache-2.0，依赖只有 `httpx`）把 4 个套件的数据**打进 wheel**（wheel 1.41 MB，其中 `tests.jsonl.gz` 956 KB）。装好后 `jevbench suites / estimate / eval` 全部离线可用（本机已实测，见 §6）。
2. **Kev 与 JevBench 接口零适配，已实测。** `kev/serve.py` 提供 `POST /v1/systemone`，请求体 `{model, state, questions}`、响应 `{model, answers, usage, latency_ms}`；JevBench 客户端发同样的三个键、读 `answers`，多余字段（`confidence/legend/usage`）被忽略。本机用 **`python -m kev.serve --run jaredpalmer/kev-0.8b --device cpu`** 起真模型，`jevbench check` 直接通过（§6.6）。
3. **打分口径**：单条关系 `score = 1 − 违反率`（容差 0.05），维度 = 其关系的均值，总分 = 5 维均值（五维都测才给总分）；mini 每关系 24 tests，`min_n=5`。
4. **官方规模**：jevbench-240 = 240 cases / 2,240 questions / 12 domains ×20 / **12,000 tests / 10,320 requests**；**jevbench-mini = 1,200 tests / 1,248 requests**（默认，也是"发榜口径"）。
5. **Kev-4B 已在官方榜上**：JevBench-mini overall **71.9**、accuracy **87.9%**、名次区间 9–15（`leaderboard.jsonl`，2026-10-28 读取）。这是我们的直接对照基线。
6. **耗时**：官方 `bench/timings.json` 记录 Kev-4B 在单张 A100 40GB 上 mini = 1,248 请求 / **103 s**、240 = 9,072 请求 / 536 s。**本机 CPU 实测 2.7 s/请求**（kev-0.8b，43 请求 116.6 s）→ CPU 跑 mini 约 56 分钟；7900 XT 估算 mini **3–10 分钟**、240 **15–45 分钟**（GPU 部分**待核实**，需静默时段后实测）。
7. **提交**：官网/README 均无公开提交表单，只有作者邮箱 `c.feng@qub.ac.uk` 与 `bench/models/<name>.sh` 的可复现规范。**要上榜 = 公开权重 + 钉住 revision + 可复现 serve 脚本 + 报告 JSON，然后邮件联系**（邮件是否为唯一入口：**待核实**）。
8. **命名陷阱**：至少存在**两个不同的 "JevBench"**——本报告的 coherence 版（`jevbench.github.io`），以及 `leanmcp.github.io/jevbench`（accuracy 型、多语言、有 Submit 页，代码 MIT）。别处写的 "JevBench v1.5.4" 指的是后者（见 §1）。

---

## 1. 口径与命名澄清

| 名称 | 归属 | 类型 | 关键差异 |
|---|---|---|---|
| **JevBench**（本报告主线） | Chen Feng, ML Lab, Queen's University Belfast；`jevbench.github.io` | 中立排行榜 + PyPI harness | **coherence**（变形关系，无 gold），50 关系 / 5 维，v0.1.0 |
| "JevBench"（同名） | `leanmcp.github.io/jevbench` | 中立排行榜（accuracy 型） | 有 Index / Results / Datasets / Multilingual / **Submit** 页，"代码 MIT，数据集各自许可"；被 `ywchiu/jev_benchmark` 引作 "JevBench v1.5.4" |
| **Decision Index** | 社区 Space `multimodalart/jev-decision-index` | 中立（社区维护）复合榜 | Full score = 60% 私有同技能测试 + 40% 新域私有任务；公开部分 37 benchmarks / 5 areas |
| **Kev suites** | `jaredpalmer/kev` + HF `jaredpalmer/kev-suites` | 工程 harness + 发布表 | decision-v1/v2、breadth-v1、hard-v1…；breadth-v1 test 分区**不公开**（私镜像） |
| **System One Bench** | `alilibx/system-one-bench` / `systemonebench.dev` | 中立排行榜（accuracy/校准/延迟/成本） | 20 模型、16 文本 + 6 图像数据集、EN/FR/AR，"byte-identical requests" |

> 结论：谈"JevBench 分数"时必须写清楚是** coherence（无 gold）**还是**accuracy 型**，两者不可比。

---

## 2. 榜单 / 基准总表

### 2.1 中立排行榜（第三方维护，非厂商自评）

| 名称 | 类型 | 入口 URL | 规模 / 维度 | 许可 / 访问 | 能否收集题目 | 备注 |
|---|---|---|---|---|---|---|
| **JevBench（coherence）** | 排行榜 + harness | https://jevbench.github.io ｜ https://github.com/JevBench/jevbench ｜ https://pypi.org/project/jevbench/ | 240 cases / 2,240 questions / 12 domains / **12,000 tests** / 50 relations / 5 dims；mini 1,200 tests | 代码+数据 **Apache-2.0**；数据随 wheel，也托管 HF（`JevBench/jevbench`，apache-2.0，67 文件，含 `gold/gold.jsonl` 与全部 `results/**/*.json.gz`） | **是**（`cases.jsonl` 780 KB 随包） | 无 gold 也能评（变形关系）；accuracy 另列；21 模型 + 4 参考模型 |
| **JevBench（leanmcp，同名异家）** | 排行榜 | https://leanmcp.github.io/jevbench/ | 多数据集 × 多模型矩阵 + Multilingual 页 | 代码 MIT，数据集各自许可；有 **Submit** 页 | **需确认条款**（页面未给数据再分发许可） | 与我们主线**不是同一个东西**，引用时务必带域名 |
| **Decision Index（社区）** | 复合排行榜 | https://huggingface.co/spaces/multimodalart/jev-decision-index | 公开 37 benchmarks / 5 areas + **私有**同技能测试与新域任务；单模型详情页 `index.html?model=<engine>` | Space 静态站，公开可读；**私有测试永不公开** | 公开部分：**是**；私有部分：**否** | 排名靠"不可训练"的私有测试；贡献方式 = 对 Space 提 PR（`ITEMS` 数组） |
| **System One Bench** | 排行榜（accuracy/校准/延迟/成本） | https://systemonebench.dev ｜ https://github.com/alilibx/system-one-bench | 20 模型；16 文本 + 6 图像数据集；EN/FR/AR；冻结数据 + 逐字节相同请求 | 仓库/release 公开；数据"frozen"由 CI 校验 | **是**（frozen data 在仓库） | 与我们互补：它给 accuracy/成本，JevBench 给 coherence |
| **Benchmark Heaven** | 聚合站 | https://benchmarkheaven.com/ | 有 "Jev-class models / Image JevBench / AudioJevBench" 标签页 | 网页公开；有 Submit a model | 否（聚合指标，不给题） | 只做导航与对比，不发布题目 |

### 2.2 vendor 发布表（厂商自评，不可当中立证据）

| 名称 | 类型 | 入口 | 规模 / 维度 | 许可 / 访问 | 能否收集题目 | 备注 |
|---|---|---|---|---|---|---|
| **TypeSafe Jev** | 托管 API（闭源权重） | https://docs.typesafe.ai ｜ console: https://console.typesafe.ai/keys | 3 primitives（Choice/Score/Noul）；`model="jev-latest"` | **托管、需 API key**；权重/RLCD 算法**未公开**（社区页明确列为"仍未开源"）；**未找到公开定价页**（`/pricing` 404，**待核实**） | **否**（无公开题集；只能自造 state/questions） | 所有开源复现都以它为参照；`typesafe-sdk` 可指向本地端点 |
| **Laya** | 开源模型 + 自带 harness | https://github.com/NandhaKishorM/laya ｜ https://pypi.org/project/laya/ ｜ HF `convaiinnovations/laya` | 421M ModernBERT-large；`laya`(512 ctx, EN) / `laya-typed-decisions`(1024 ctx) / multilingual | **Apache-2.0**（PyPI 0.4.15；HF card apache-2.0，5,836 likes） | 是（自家数据/仓库） | 厂商自评：typed-decisions 基准 2,000 决策上 0.766 vs base 0.362；JevBench 客观分 56.5 / 63.9（见 §2.4） |
| **OpenJev** | 开源模型族 | https://github.com/alanhuangyoo/OpenJev ｜ PyPI `wev-ai`(0.2.2) / `openjev-ai`(0.2.1) ｜ HF `alanhuangya/OpenJev-1.7B/4B/8B` | 1.7B / 4B / 8B（`OpenJev-9B` 亦在 JevBench 榜，overall 83.9 第 1） | **Apache-2.0**；Zenodo DOI 10.5281/zenodo.22941164 | 是（HF 数据集 `OpenJev-Data`） | 厂商宣称"开源本地替代 Jev"；其 9B 是 JevBench 榜首 |
| **OpenDecider** | 开源模型族 | https://github.com/manjunathshiva/opendecider ｜ PyPI 0.9.0 ｜ HF `opendecider-nano/small` | nano / small；CPU/NVIDIA/Apple | **Apache-2.0** | 是 | 厂商表：与 Jev / Microsoft-Decision-1 / Laya / CLM-8B / 前沿 LLM 同题同 scorer 对比（自评） |
| **Kev 1.0** | 开源模型族 | https://github.com/jaredpalmer/kev ｜ HF `jaredpalmer/kev-0.8b/4b/9b/27b` | 0.8B / 4B / 9B / 27B；LoRA + pointer head on Qwen3.5 Base | **Apache-2.0**（repo + 权重卡） | 部分（见 §2.3 的 breadth-v1 限制） | README 的 "Held-out datasets index"：0.8B 23.3 / 4B 38.0 / 9B 41.0 / 27B 52.3；Jev 54.0 |

### 2.3 工程 harness（跑分基础设施，不是榜）

| 名称 | 类型 | 入口 | 规模 / 维度 | 许可 / 访问 | 能否收集题目 | 备注 |
|---|---|---|---|---|---|---|
| **jevbench（CLI/库）** | harness | `pip install jevbench`（0.1.0，2026-09-30 发布） | 4 套件：`examples`(1 case/50 tests)、`jevbench-mini`(1,200/1,248 req)、`jevbench-240`(12,000/10,320 req)、自带 `datagen` | Apache-2.0；依赖 `httpx>=0.27`；Python ≥3.10 | **是**（`cases.jsonl`） | 支持 HTTP、Python 函数、fake 后端；请求级磁盘缓存 |
| **kev suites** | harness + 数据 | 本地 `~/src/kev/evals`；HF `jaredpalmer/kev-suites`（125 文件，**无数据卡/无 license 字段**） | decision-v1/v2、hard-v1（7 families × 6 模板）、breadth-v1、documents-v2、transfer-v2、public-pool-v4/5/6、external/scienthoon-v1、external/semif-v1 | 代码 Apache-2.0；**数据按各 manifest 的 rights 字段**；breadth-v1 分区在**私有镜像** | 多数：是；breadth-v1 分区：**否**（见下） | `--allow-test` 读锁定的 test 分区 |
| **JevBench 的 bench/** | harness | `bench/run_model.sh`、`bench/models/*.sh`、`bench/timings.json` | 21 个模型的 serve 规范（含 `kev-4b.sh`） | Apache-2.0 | — | 官方复现入口；`serving.json` 记录 2 个"非官方 server"的例外 |

**breadth-v1 的许可边界（重要）**：`evals/breadth-v1/manifest.json` 明确写：分区**只存在于私有镜像**，理由是若干来源不允许再分发——SATA-Bench **CC-BY-NC-4.0**、SGD **CC-BY-SA-4.0**、Humicroedit **无许可**、cfcolor **仅代码声明**；仓库里只有 manifest。`mirror_note` 记录 2026-09-24 冻结后加入镜像，分区字节一致（sha256 在 `files`）。

**`--allow-test` 的风险**：`kev/suite.py:204-209` 对 `split="test"` 直接抛错 —— "locked test requires explicit --allow-test; never use it for search"；`kev/benchmark.py:182`、`kev/rounds.py:518`（`locked_test` 入口）都把它当"注册确认阶段"。风险不是技术性的，而是**方法学**：反复用 test 调方案 = 污染榜面。我们只应在"定版确认"时读一次，并记录在任务页。

### 2.4 JevBench 官方榜上的相关模型（`leaderboard.jsonl`，2026-10-28 读取，共 25 行 = 21 模型 + 4 参考）

| 模型 | overall | REP | BAT | MEA | LOG | CHO | accuracy | 名次区间 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Open-Jev-9B | **83.9** | 81.9 | 100.0 | 50.2 | 87.1 | 100.0 | 88.4% | 1–2 |
| JevAny-Gemma-4B (pointer) | 81.2 | 81.4 | 100.0 | 52.0 | 83.8 | 88.9 | 87.6% | 1–7 |
| **Kev-4B** | **71.9** | 74.4 | 100.0 | 30.1 | 67.5 | 87.5 | **87.9%** | **9–15** |
| CLM (8B) | 66.8 | 59.2 | 100.0 | 25.5 | 49.6 | 100.0 | 63.5% | 15–19 |
| Laya-typed (421M) | 63.9 | 55.0 | 100.0 | 14.5 | 73.8 | 76.4 | 71.0% | 16–20 |
| Verdict | 59.4 | 66.1 | 100.0 | 19.9 | 77.9 | 33.3 | 64.2% | 18–21 |
| Laya (421M) | 56.5 | 52.5 | 100.0 | 16.4 | 67.9 | 45.8 | 70.8% | 20–21 |
| *Uniform（忽略输入）* | *89.4* | *100* | *100* | *47.1* | *100* | *100* | *39.8%* | 参考 |

**读法（官方反复强调）**：coherence 不是正确率。均匀回答的模型 overall 89.4（高于所有真实模型），accuracy 只有 39.8%（等于瞎猜）。**任何 JevBench 分数必须与 accuracy/校准并列汇报**，否则是误导。

---

## 3. JevBench 细节

### 3.1 数据规模与来源（以 wheel 内 manifest 为准）

| 套件 | cases | questions | tests | requests | 说明 |
|---|---:|---:|---:|---:|---|
| `jevbench-240` v1 | 240 | 2,240 | **12,000** | **10,320** | 12 domains × 20；50 relations；seed 0；从 83,964 trials 中选 12,000 |
| `jevbench-mini` v1（默认/发榜） | 240 | — | **1,200** | **1,248** | 每关系每域 2 cases（24 tests/关系）；`drawn_from: jevbench-240 v1` |
| `examples` v2 | 1 | 7 | 50 | ≤50 | 手写客服 case，秒级，`min_n=1`，**只用于验证链路** |

- 生成方式：`datagen` 事实优先合成，writer `openai/gpt-oss-20b`（vLLM），verifier `Llama-3.1-8B`；state 长度上限 480 tokens。
- 改写库（paraphrase / negation / description / translate:zh）：生成+AI 复核（Claude，2026-10-01）**823 kept / 345 audited:false**，**未经人工审校**（manifest 原话 "not human-audited"）。
- 包内文件尺寸：`tests.jsonl.gz` 956 KB、`cases.jsonl` 780 KB、`rewrites.jsonl` 808 KB → **完全可离线**。

### 3.2 评测接口（wire format，逐字段确认）

请求（jevbench → 模型）——本机 stub 抓到的真实请求体只有这三个键：

```json
{"model":"kev-latest","state":"<case 的 state，永不改写>",
 "questions":{"primary_team":{"type":"choice","instructions":"...","criteria":{"engineering":"...","billing":"..."}},
              "export_failing":{"type":"noul","instructions":"..."},
              "frustration":{"type":"score","instructions":"...","criteria":["Calm","Mildly annoyed","Clearly frustrated"]}}}
```

响应（模型 → jevbench）——Kev 的 `kev/api.py:149 to_answers()` 产出的正是这个形状：

```json
{"answers":{"export_failing":{"type":"noul","noul":0.93},
            "primary_team":{"type":"choice","choice":"engineering","confidence":0.21,
                            "probabilities":{"engineering":0.47,"billing":0.28,"shipping":0.25}},
            "frustration":{"type":"score","score":1.44,"confidence":0.34,
                           "legend":{"0":"Calm","1":"..."},"probabilities":{"0":0.0,"1":0.56,"2":0.44}}}}
```

- 规则：Noul = `[0,1]` 的"是"概率；Choice 必须给**每个** option id；Score 必须给 `"0".."n-1"`（或每层文本）；Choice/Score 会被重归一化。
- **4xx = 拒答**（计入 errors，相关关系不打分）；**429/5xx 重试**。Bearer token 读 `JEVBENCH_API_KEY`。
- 其他模型字段（`choice/score/legend/usage/latency_ms`）**被忽略**，所以 Kev 多返回的字段无害。

### 3.3 五维度与 50 关系

| 维度 | 含义 | 关系数 | 典型法则 |
|---|---|---:|---|
| **REP** Representation | 同一事件换说法/换序/换语言，答案不变 | 15 | 选项重排后概率跟着选项走 |
| **BAT** Batch independence | 答案不依赖同批其他问题、顺序、数量 | 5 | 批次倒序，答案不变 |
| **MEA** Probability measure | 概率可加：q 与 ¬q 和为 1；合并选项概率相加 | 17 | 互补、分割、边缘化 |
| **LOG** Logical order | 合取 ≤ 任一分量；更严阈值 ≤ 更松阈值 | 10 | Fréchet bounds、单调性 |
| **CHO** Choice-set conditioning | 增删无关选项不改变其余选项的相对概率 | 3 | IIA / conditioning |

合计 50。另有 **diagnostics**（不打分，需显式 `--diagnostics` 才跑，如 `--minimize` 的 `no-batch%`）。

### 3.4 分数怎么算

- **test**：一个关系 × 一个 case 的一个问题（有些关系把多个 variant 判在一起，任一违反即失败）。
- **relation**：`score = 1 − 违反率`（容差 0.05），另有 `graded = 1 − 归一化的超容差量`；两者同读。
- **dimension** = 其关系均值；**group** 只是重分组（不加权，不改分）；**overall** = 5 维均值，**缺一维则不给总分**。
- **`min_n=5`**：测试数 < 5 的关系不计入均值（所以 mini 的 24 tests/关系够用，`examples` 的 1 test/关系只算演示）。
- 区间：Wilson 95%（每关系）+ bootstrap 1000 次（overall）；**mini 的区间宽度约为 240 的 2.5 倍（4.4 vs 1.7 分）**，相差几分应视为并列。

### 3.5 CLI / Python API（本机实测，2026-10-28）

装（**不进项目 venv**）：

```bash
python3 -m venv /tmp/jevbench-venv
/tmp/jevbench-venv/bin/pip install jevbench==0.1.0     # 只拉 httpx 等 6 个包
```

子命令（`jevbench --help` 实测）：`run | check | eval | estimate | plan | suites | report | rewrite | relations | taxonomy | datagen`。

关键参数（`eval`）：`--url --model --revision --suites/--suite --cases --domains --dimensions --groups --relations --diagnostics --repeats --concurrency --seed --minimize --max-requests --rewrites --tolerance(0.05) --cache-dir(.jevbench-cache) --no-cache --name --out`。
`report`：`--level dimension|group|relation|domain --card --json --radar --grid --families --family-dir --min-n --bootstrap --metric binary|graded`。

实测输出（`--backend fake:coherent --suite examples`，0.14 s）：

```
fake:coherent: overall 65.0  (1 cases, 50 scored relations, tolerance 0.05)
  REP 53.3  BAT 100.0  MEA 11.8  LOG 60.0  CHO 100.0
```

`estimate` 实测：mini `{"cases":240,"relations":50,"requests":1248,"trials":1200}`；240 `{"requests":10320,"trials":12000}`。

### 3.6 排行榜提交要求

- **没有公开提交入口**：官网只有 "Get started"（`jevbench check/eval`）与联系邮箱；GitHub README 结尾是 "Issues and contributions"。
- 官方复现路径 = `bench/models/<name>.sh`（钉住 release/revision + 启动命令 + 已知未决项）+ `bench/run_model.sh`，报告存 `runs/jevbench-<suite>/<name>.json`，并公开在 `JevBench.github.io` 的 `data/results/<suite>/<model>.json.gz`。
- 因此**事实上榜条件**（依据 `bench/models/kev-4b.sh` 的写法）：公开权重 + 钉住 commit/revision + 可复现 serve 命令 + 完整报告 JSON。**是否只接受邮件申请、是否要求公开 endpoint：待核实**（发邮件问 `c.feng@qub.ac.uk`）。
- 不需要付费、不需要账号。

---

## 4. Kev suites / Decision Index / `--allow-test`

- **数据**：`~/src/kev/evals` 下 decision-v1（train 2.47 MB / dev 1.02 MB / test 1.02 MB / cal 325 KB）、decision-v2（4.80 / 1.71 / 1.71 / 0.62 MB）、hard-v1（dev 2.63 MB / test 2.60 MB / 7 families × 6 模板，模板 0-3 训练、4 dev、5 test）、transfer-v2、public-pool-v4/5/6、external/{scienthoon-v1,semif-v1}；`breadth-v1`、`documents-v2` 本地**只有 manifest**。
- **HF 镜像** `jaredpalmer/kev-suites`：125 文件、10 likes、4,585 downloads、**无 README/数据卡**（`cardData` 为空）→ 许可必须逐 manifest 读 `rights`/`mirror_note`，不能假设 Apache-2.0 覆盖数据。
- **Decision Index（Kev 口径）**：README 的 "Held-out datasets" 是社区 Decision Index 的 chance-corrected index，**只在 breadth-v1 的 test 分区**上算；Kev-0.8B 23.3 / 4B 38.0 / 9B 41.0 / 27B 52.3，Jev 54.0。注意它与社区 Space 的 "Full score"（60% 私测 + 40% 新域私测）**不是同一个数**，别混用。
- **`--allow-test`**：见 §2.3。我们若要"对标官方 Kev 数字"，读 breadth-v1 test 需要私有镜像（本地没有）+ 一次确认性读取，**不建议在 JevBench 调研阶段碰**。

---

## 5. Runbook：用 Kev 跑 JevBench（精确命令）

### 5.0 前置结论

- **零安装即可 serve**：本机实测 `PYTHONPATH=/home/wenbo/src/kev ~/src/polgov/.venv/bin/python -c "import kev.serve"` 成功（fastapi/uvicorn/accelerate/sklearn/peft/transformers 全在，只有 `typesafe_sdk` 缺——serve 不需要它）。**因此不需要往 `~/src/polgov/.venv` 装任何东西**。
- **版本张力（待核实）**：`kev/pyproject.toml` 写 `torch>=2.6,<2.9`，本机是 `2.9.1+rocm7.2.1`。import 通过；**实际推理未验证**（静默时段）。若 ROCm 路径出问题，退路见 §5.5。
- **state 长度不会触发 422**：JevBench datagen 把 state 限制在 480 tokens；本机 `/v1/models` 实测 `max_state_tokens: 65536`（kev-0.8b），README 另标的 validated context 8,192 指精度而非硬限。两者都远大于 480。

### 5.1 一次性准备（CPU/网络，随时可做）

```bash
# 1) jevbench：独立 venv，绝不进项目 venv
python3 -m venv /tmp/jevbench-venv
/tmp/jevbench-venv/bin/pip install jevbench==0.1.0
/tmp/jevbench-venv/bin/jevbench suites          # 应列出 examples / jevbench-240 / jevbench-mini
/tmp/jevbench-venv/bin/jevbench estimate --suite jevbench-mini   # 1248 请求

# 2) 预取权重（可选，避免 serve 时卡在下载）
export HF_HOME=/tmp/hf-kev
~/src/polgov/.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("jaredpalmer/kev-4b")
PY
```

### 5.2 跑分（**需要 GPU → 只能在 09:30 之后**）

```bash
# --- 终端 A：serve（GPU）---
cd /tmp
export HF_HOME=/tmp/hf-kev
export PYTHONPATH=/home/wenbo/src/kev
~/src/polgov/.venv/bin/python -m kev.serve \
  --run jaredpalmer/kev-4b --host 127.0.0.1 --port 8009
# 设备默认 auto：先探 CUDA(含 ROCm)，失败才 MPS/CPU。要强制：--device cuda
# 可选环境变量：
#   KEV_DTYPE=bf16          （GPU 默认 bf16；fp32 仅用于对照官方 eval 路径）
#   KEV_PREFIX_CACHE=4      （state 前缀缓存条数，JevBench 同一 state 反复问，命中率高）
#   KEV_TRUNCATE_STATES=0   （默认；超长 state 直接 422 而非静默截断——我们要的是"拒答"可见）
#   KEV_API_KEY=<key>       （设了就要求 Bearer；本地默认不设=开放）

# --- 终端 B：先体检（CPU 侧，1 次请求）---
/tmp/jevbench-venv/bin/jevbench check \
  --url http://127.0.0.1:8009/v1/systemone --model kev-latest

# --- 终端 B：正式跑（mini = 发榜口径；1,248 请求）---
cd /tmp && mkdir -p jev-runs
/tmp/jevbench-venv/bin/jevbench eval \
  --url http://127.0.0.1:8009/v1/systemone \
  --model kev-latest --name kev-4b \
  --suite jevbench-mini --concurrency 1 \
  --out /tmp/jev-runs/kev-4b-mini.json

# 可选：全量 240（12,000 tests / 10,320 请求，时间 ×8）
#   --suite jevbench-240 --out /tmp/jev-runs/kev-4b-240.json
# 可选：只跑某维，先看趋势
#   --dimensions MEA,LOG
```

**为什么 `--concurrency 1`**：官方测得并发会让部分 server 的判定翻转（vLLM 上 1,181 个判定里 19 个变了），且多数 Jev server 串行更快；要加速请用**多副本 URL**（逗号分隔，同模型不同端口），不要提并发。

### 5.3 产物

| 路径 | 内容 |
|---|---|
| `/tmp/jev-runs/kev-4b-mini.json` | 完整报告：每关系/每 check 的违反率、Wilson 区间、平均偏差、argmax 翻转率、最差样例的完整请求 |
| `/tmp/jev-runs/.jevbench-cache/`（在 cwd 下） | 请求级缓存，按 `backend+request+repeat` 键；**中断可续跑**，重跑不重复计费/计时 |
| stdout | dimension 表 + group 表（可直接贴报告） |
| `jevbench report <a.json> <b.json> --json x.json --radar r.svg` | 多模型对比、雷达图、coherence card |

### 5.4 耗时 / 显存（CPU 行为**实测**；GPU 行为**估算**，待静默时段后核实）

| 项 | 官方（A100 40GB，`bench/timings.json`） | 本机 7900 XT 20GB 估算 |
|---|---|---|
| kev-4b mini（1,248 req） | **103 s** | **3–10 min** |
| kev-4b 240（9,072 req，去缓存后） | **536 s** | **15–45 min** |
| kev-0.8b mini | —（官方未列） | 1–3 min（若显存/驱动紧张的首选） |
| CPU（`--device cpu`） | jevhome-ettin-1b mini = 3,812 s（官方 CPU 节点） | **实测 2.7 s/请求**（43 请求 / 116.6 s）→ kev-0.8b mini（1,248 req）≈ **56 min** |

- 显存：kev-4b bf16 权重约 8–9 GB + KV/前缀缓存（`KEV_PREFIX_MAX_TOKENS` 默认 65,536）→ 20 GB 卡**够**；kev-9b bf16 约 18 GB，**紧张**（建议 `KEV_PREFIX_CACHE=2`）；kev-27b 不可能。
- 首跑另加**下载时间**（kev-4b adapter + Qwen3.5-4B-Base，数 GB，取决于网络）。
- 现在（约 00:40）**不能跑**：§5.2 整体落在 00:30–09:30 静默时段内；CPU 路径（§5.1 + `--device cpu`）随时可跑。

### 5.5 失败模式与替代方案

| 失败 | 现象 | 处置 |
|---|---|---|
| ROCm 路径起不来（torch 2.9 vs pin <2.9） | serve 启动即报 kernel/后端错误 | ①`--device cpu` 跑 kev-0.8b（CPU 允许，慢但可用）；②在 `/tmp/kev-venv` 另建 venv，装 `torch==2.8.*+rocm` 再 `uv pip install -e ~/src/kev --no-deps` + 手动补依赖（**ROCm 2.8 wheel 是否存在：待核实**） |
| state 超长 422 | jevbench 记 errors，相关关系不打分 | 本基准 state ≤480 tokens，正常不会发生；不要开 `KEV_TRUNCATE_STATES=1`（会静默截断，答案不可比） |
| 服务端串行太慢 | mini 超过 ~30 min | 起 2 个副本（两个端口、同一 checkpoint，显存不够就 0.8b），`--url u1,u2` |
| 排行榜不认 | 邮件无回复 / 要求额外材料 | 自建对照表：JevBench 报告 + accuracy（需 gold，来自 HF `gold/gold.jsonl`）+ 延迟；对外称"reproduced, not listed" |
| 只想要"能否上榜"的快速答案 | — | 先跑 mini（3–10 min），与官方 kev-4b 的 71.9 对齐；差异 >2 分再查 serve 参数 |

### 5.6 Kev 是否自带 Jev/System One 兼容层

- **`kev/serve.py`：是。** `POST /v1/systemone`（`serve.py:249`）、`GET /v1/models`（`:298`）、`x-typesafe-request-id` 响应头、`KEV_API_KEY` bearer 校验（`:236`）、`model` 接受 `kev-latest` 与 `jev-latest`（`:35`）。额外还有 `/v1/systemone/permute`、`/v1/systemone/separate` 两个 demo 端点（jevbench 不用）。
- **`kev/jev.py`：不是 JevBench 适配器。** 它是"通过 Vercel AI Gateway 付费调用 **TypeSafe 托管 Jev**（`kev/predictors.py:273 JevPredictor` → `playground/scripts/jev-evaluate.mjs`）在 **kev 自己的 development 分区**上打分"的脚本，要 `AI_GATEWAY_API_KEY` 或 `--provision-scope`（$1、7 天 key），带 `--budget/--max-calls` 预算闸。**与 JevBench 无关，也不该用它跑 JevBench**。
- 另一条现成路径：`kev/predictors.py:163` 的 `SystemOnePredictor` 会 `POST <base_url>/v1/systemone`——这正是 JevBench 用的端点，所以我们**自己的 serve 既能被 kev 评，也能被 jevbench 评**。

---

## 6. 本机实测证据（2026-10-28，全部 CPU）

1. **包与数据**：`pip download jevbench --no-deps` → `jevbench-0.1.0-py3-none-any.whl`（1,409,108 B）；解包见 4 个套件目录；`METADATA` 确认 `License-Expression: Apache-2.0`、`Requires-Dist: httpx>=0.27`、`Requires-Python >=3.10`。
2. **独立 venv 安装**：`/tmp/jevbench-venv` 装 7 个包（jevbench 0.1.0 + httpx 0.28.1 等），`jevbench --help`、`suites`、`estimate` 正常；`eval --backend fake:coherent --suite examples` 0.14 s 出分（overall 65.0）。
3. **wire 兼容（两步验证）**：先写了复刻 `kev/api.py to_answers()` 形状的 stub（`POST /v1/systemone`，返回 noul/choice/score + confidence/legend/usage/latency_ms），jevbench 结果：
   ```
   jevbench check: OK. systemone:kev-latest@http://127.0.0.1:18080/v1/systemone answered one request
   (4 noul, 2 choice, 1 score) in the standard Jev format in 0.007s
   ```
   `examples` 全 50 关系跑通并写出报告。抓到的请求体键为 `["model","questions","state"]`，与 `kev/api.py SystemOneRequest` 完全一致。
4. **kev.serve 可导入**：`PYTHONPATH=~/src/kev ~/src/polgov/.venv/bin/python -c "import kev.serve"` → `MODEL_NAMES ('kev-latest','jev-latest')`；`typesafe_sdk` 缺失不影响 serve。
5. **GPU 未使用**：无任何 torch.cuda 计算、无模型加载；`rocm-smi` 在本 WSL 不可用（`amdgpu not found in modules`），设备经 torch 探测为可用（`torch.cuda.is_available() == True`，hip 7.2.53211）。
6. **真模型端到端（关键，CPU）**：`PYTHONPATH=~/src/kev HF_HOME=/tmp/hf-kev <项目 venv>/python -m kev.serve --run jaredpalmer/kev-0.8b --device cpu --port 18081`，**105 s 后 ready**（含下载 1.8 GB 缓存），`/v1/models` 报 `device=cpu, backend=torch, dtype=float32, temperature=2.35, max_state_tokens=65536, release_date=2026-10-01`。随后：
   - `jevbench check` → **OK**，"answered one request (4 noul, 2 choice, 1 score) in 2.724s"；
   - `jevbench eval --suite examples` → **43 请求 / 116.6 s（≈2.7 s/请求；serve 日志共 44 次 POST，含 check 的 1 次）**，overall **66.4**（REP 40.0 / BAT 100.0 / MEA 17.6 / LOG 60.0 / CHO 100.0；`examples` 每关系仅 1 test，**只作链路证明，不是成绩**）；
   - 全程无 GPU 调用，报告落在 `/tmp/jev-runs/kev-0.8b-examples.json`。
7. **结论**：`check`/`eval`/`report` 全链路在**不安装任何东西进项目 venv**的前提下成立，唯一未验证项是 GPU(ROCm) 路径。

---

## 7. 后续收集建议

1. **先 mini 后 240**：mini 与 240 在 17 个模型上 overall 相关 Pearson 0.993 / Spearman 0.978，排名位移 ≤2 —— 用 mini 做日常回归，定版再跑 240 收窄区间（区间 4.4 → 1.7 分）。
2. **建立"三件套"汇报格式**：coherence（5 维 + overall + CI）、accuracy（gold 取自 HF `gold/gold.jsonl`，与官方 accuracy 列对齐）、延迟/成本。单独报 coherence 会被 uniform 89.4 打脸。
3. **对标锚点**：kev-4b = 71.9（`leaderboard.jsonl` 第 12 行，名次区间 9–15）；若我们微调后 >76（进前 8）才谈得上"改善"。同时跑 `KEV_DTYPE=fp32` 与 bf16 各一次，确认数值路径差异（官方 eval 用 fp32）。
4. **别混口径**：JevBench-mini 与 Decision Index Full score、与 leanmcp 的 JevBench、与 System One Bench 的 accuracy 榜，**都不可直接比较**；对外只报"JevBench-mini coherence + accuracy"并附来源。
5. **可复用的题型**：`cases.jsonl` 的 `state + questions` 是通用格式，可直接当我们 POL 数据的外部压力测试集（注意：**不要**把 JevBench 的题拿去训练/蒸馏，会污染公开榜的可比性）。
6. **备选榜位**：System One Bench（accuracy/成本）与 Decision Index（复合）都接受提交；如果 coherence 榜沟通不畅，可作为第二落点。
7. **待观察**：JevBench 0.1.0 之后是否加 v2 关系/新套件（CHANGELOG 只有 820 B，暂无）。

---

## 8. 许可与数据边界提示

| 资产 | 许可 | 可做 | 不可做 |
|---|---|---|---|
| jevbench 代码 + 4 套件数据 | **Apache-2.0**（含 NOTICE：与 TypeSafe 无关） | 任意使用/再分发/商用；题目可入库 | 声称是 TypeSafe 官方评测 |
| JevBench 榜单与 `results/**` | Apache-2.0（HF 数据集 apache-2.0） | 引用分数、复算 | 把别人报告改名当自己的 |
| kev 代码 | Apache-2.0 | 使用/改 | — |
| `jaredpalmer/kev-suites` 数据 | **无数据卡**，逐 manifest `rights` | 按各 manifest 允许的用途 | 假设 Apache-2.0 覆盖数据；再分发 breadth-v1 |
| `breadth-v1` test 分区 | 私镜像（SATA-Bench CC-BY-NC-4.0、SGD CC-BY-SA-4.0、Humicroedit 无许可、cfcolor 仅代码） | 内部一次确认性评测 | 公开、上传、进训练、进 Agent 上下文 |
| TypeSafe Jev API | 商业条款（**未找到公开定价页**，待核实） | 按 key 使用 | 声称权重开源；转售 |
| Laya / OpenJev / OpenDecider / Kev 权重 | Apache-2.0 | 本地跑、微调、商用（遵守各自卡片） | — |

**纪律**（与仓库 `AGENTS.md` 一致）：公开测试只做回归，不进梯度/教师/阈值；私有保留集不进任何公开分支、日志、截图或 Agent 上下文。JevBench 是**公开**基准，可以进仓库与报告，但**不要**把它的题混进训练集。

---

## 9. 待核实清单

1. 本机 ROCm 上 `kev-4b` 在 torch 2.9.1 下的实际推理是否正常（pin 写的是 <2.9）——CPU 路径已验证，GPU 路径**未验证**，静默时段后第一步。
2. 本机 GPU 跑 mini 的实测耗时（估 3–10 min）与显存峰值。
3. JevBench 是否接受邮件以外的方式上榜、是否要求公开 endpoint（README 只给邮箱）。
4. TypeSafe Jev 的公开定价（`/pricing` 404；docs 无价格页）。
5. `leanmcp.github.io/jevbench` 的数据许可与提交条款（页面仅写"datasets keep their own licences"）。
6. ~~CPU smoke 结果~~ → **已验证通过（§6.6）**：零安装 + 真权重 + jevbench 全链路。剩余未知仅 GPU/ROCm 与耗时。

---

## 10. 来源（全部 2026-10-28 抓取）

- JevBench 官网：https://jevbench.github.io/
- JevBench 仓库/README/timings：https://github.com/JevBench/jevbench ｜ `bench/timings.json` ｜ `bench/models/kev-4b.sh` ｜ `docs/reproducing.md`
- PyPI：https://pypi.org/project/jevbench/ （0.1.0，2026-09-30）
- HF 数据集：https://huggingface.co/datasets/JevBench/jevbench （apache-2.0，67 文件，含 `data/leaderboard.jsonl` 25 行）
- Kev：https://github.com/jaredpalmer/kev ｜ https://huggingface.co/datasets/jaredpalmer/kev-suites ｜ 本地 `~/src/kev/evals/*/manifest.json`
- Decision Index（社区）：https://huggingface.co/spaces/multimodalart/jev-decision-index
- System One Bench：https://systemonebench.dev ｜ https://github.com/alilibx/system-one-bench
- 同名 JevBench（leanmcp）：https://leanmcp.github.io/jevbench/
- TypeSafe：https://docs.typesafe.ai/introduction/quickstart.md ｜ https://docs.typesafe.ai/concepts/system-one.md
- Laya：https://github.com/NandhaKishorM/laya ｜ https://pypi.org/project/laya/ ｜ https://huggingface.co/convaiinnovations/laya
- OpenJev：https://github.com/alanhuangyoo/OpenJev ｜ https://pypi.org/project/wev-ai/ ｜ https://pypi.org/project/openjev-ai/
- OpenDecider：https://github.com/manjunathshiva/opendecider ｜ https://pypi.org/project/opendecider/
- 第三方 Jev 评测随笔：https://github.com/ywchiu/jev_benchmark ｜ https://benchmarkheaven.com/