# POL2 Steward

POL2 Steward（POL2 治理管家）是面向 Agent 的独立治理代理，不绑定任何特定 Agent、客户端、运行环境或模型供应商。不同产品、业务系统和自定义 Agent 都通过适配器接入；适配器只影响覆盖能力，不改变核心治理规则。

当前仓库是试点实现，不是生产批准版本。发布包已包含运行所需的知识包；普通安装不需要重新下载理论原文或构建知识包。

## 安装

前置条件是 Python 3.10 以上，以及带 compose 插件的 Docker。

```bash
./install.sh
./start.sh
```

安装脚本会自动：

- 创建 `.venv` 并安装 Python 依赖；
- 启动本地 PostgreSQL/pgvector 容器并创建数据库；
- 生成服务令牌和许可密钥；
- 写入本地 `.env`；
- 使用随发布包附带的知识包。

默认模型地址和模型名已经预填，正常安装只需要输入 API key；如使用其他兼容服务，再修改地址和模型名：

```text
OpenAI-compatible LLM base URL
model name
API key
```

服务默认只监听 `127.0.0.1:18080`。数据库固定使用 PostgreSQL。启动后把 Agent 的模型地址设置为：

```text
http://127.0.0.1:18080/v1
```

本地简单模式不需要为每个请求添加平台标识头。需要远程访问、多工作空间或独立治理模型时，再使用高级配置。

## 当前能力

- 固定提交的 POL2 原文、概念、关系、规则、解释和可靠回答；
- 448 个原文段落、28 条候选规则、19 条可靠回答和 150 个评估案例；
- OpenAI 兼容模型代理，检查模型输入、输出和返回的工具调用；
- 六类治理结论：理论回答、放行、附条件放行、澄清、修订、拒绝；
- 项目、会话、请求去重、判定缓存和审计查询；
- PostgreSQL/pgvector 试点适配；
- 任务、运行、步骤、许可和任务时间线 API；
- 通用的执行前工具 Hook，以及一个真实宿主的端到端验收（允许写入、阻止未授权删除、执行明确授权删除）；
- 外部 PostgreSQL/pgvector 工程部署验收。

## 尚未达到生产标准

- 兼容的单次请求路径仍会重复做完整判断；任务级路径已提供，但尚未覆盖所有适配器；
- 卡片事件和任务时间线已记录，独立展示适配器尚未实现；
- 未接入 Hook 的 Agent 仍可绕过执行门禁；工具参数覆盖和跨适配器矩阵仍需扩展；
- 知识包仍是 `behavior_verified_candidate`；
- 4096 维嵌入使用精确扫描，尚未完成容量验证；
- 身份和平台访问控制尚未与 POL2 判断彻底分层；
- 高可用、不可篡改审计链、独立盲测和生产模型批准尚未完成。

当前设计基线见 [POL2 服务流程正式设计 v1.1](../docs/POL2服务流程正式设计-v1.1-20261022.md)，生产化计划见 [生产化路线图 v1.1](../docs/POL2治理服务生产化路线图-v1.1-20261022.md)，接入步骤见 [Agent 接入指南](../docs/Agent接入与部署指南-v1.0-20261022.md)。

## 开发构建与验证

普通用户不需要执行本节。维护者修改知识数据后，才需要重新构建知识包。

自动化测试使用 `service/memory_store.py` 作为隔离测试替身；运行服务和发布安装只使用 PostgreSQL，默认不会启用测试替身。

```bash
python3 tools/import_sources.py
python3 tools/validate_knowledge.py
python3 tools/build_package.py
python3 tools/build_runtime_package.py
python3 -m pytest -q tests
```

`import_sources.py` 从固定上游提交读取理论原文；`build_package.py` 会在知识校验失败时拒绝构建，并在完成后验证生成的包。

## 本地运行

```bash
POL2_ALLOW_CANDIDATE_PACKAGE=1 \
POL2_ALLOW_REFERENCE_JUDGE=1 \
POL2_DATABASE_URL='postgresql://pol2:password@127.0.0.1:15432/pol2' \
python3 -m uvicorn service.app:app --host 127.0.0.1 --port 18080
```

健康检查：

```bash
curl http://127.0.0.1:18080/health
```

## 配置治理模型

治理模型需提供 OpenAI 兼容 `/chat/completions`，并返回包含 `decision`、`reason`、`rule_ids`、`conditions`、`clarification` 和 `revision_items` 的 JSON。

```bash
export POL2_MODEL_BASE_URL='http://127.0.0.1:8000/v1'
export POL2_MODEL_NAME='your-model-id'
export POL2_MODEL_API_KEY='replace-with-secret'
export POL2_MODEL_TIMEOUT=60
```

治理模型使用独立上下文，不自动读取或转发 Agent 的凭证。

## 模型请求适配

```bash
export POL2_UPSTREAM_BASE_URL='http://127.0.0.1:8000/v1'
export POL2_UPSTREAM_API_KEY='replace-with-secret'
```

客户端把模型地址指向本服务 `/v1`。本地简单模式自动填充固定的本地账号和会话，不需要额外请求头；认证、多工作空间或远程接入时，使用 `X-POL2-Account`、`X-POL2-Session` 等字段恢复调用范围。这些字段属于平台接入信息，不参与 POL2 对内容的伦理判断。

流式请求当前会先完成治理，再以缓冲 SSE 释放，不是逐 token 实时流。

## 任务级 API

```text
POST /v1/tasks                         创建任务，执行任务入口治理
POST /v1/tasks/{task_id}/activate      确认条件，签发任务许可
POST /v1/tasks/{task_id}/steps         记录普通步骤；风险步骤升级治理
POST /v1/tasks/{task_id}/deliver       检查最终产物
GET  /v1/tasks/{task_id}/timeline      查询任务、运行、步骤、许可、卡片和审计事件
POST /v1/permits/consume               消费一次性操作许可
```

任务入口、风险门禁和最终交付会生成卡片事件；普通步骤只写入时间线，不生成卡片。当前风险升级由 `risk_flags`、步骤类型和规则触发，后续生产版还需补充跨适配器的风险分类、条件证据和完整任务许可复用。

## Agent 接入

通用适配要求见 [OpenAI-compatible adapter](adapters/openai-compatible.md)。

有副作用的工具执行前应调用通用 Hook：[hooks/pre_tool_hook.py](hooks/pre_tool_hook.py)。Hook 会检查操作、消费一次性许可，并在服务不可用、条件未满足或治理拒绝时失败关闭。

模型代理返回工具调用时，会同时记录该操作的一次性许可，并以 `session + tool_call_id` 形成稳定请求号。宿主保留 `pol2.permit` 元数据时，Hook 直接消费该许可；宿主裁掉元数据时，Hook 用稳定请求号回查同一操作记录并消费许可。两条路径都不会再次调用治理模型。只有完全没有经过模型代理、也不存在代理记录的直接工具调用，才走完整的操作治理回退。

适配器能力分为：

- `full`：模型、工具、产物和展示全部接入；
- `partial`：只接入部分控制点；
- `audit_only`：只记录，不阻止；
- `unsupported`：不支持。

只接模型代理、没有工具和产物适配的客户端，只能声明部分治理。

## 存储边界

运行环境只使用 PostgreSQL/pgvector。由于 4096 维向量超过 pgvector HNSW 的 4000 维上限，当前使用精确向量扫描。

## 安全

- 不要提交 `.env`、服务令牌、模型密钥、身份密钥、数据库密码或备份；
- 生产配置必须使用不可变知识包并通过启动校验；
- 治理服务、模型和数据库不可用时默认不放行；
- 该仓库当前不是生产可用声明。

## 许可证

代码按 MIT License 发布，见根目录 [LICENSE](../LICENSE) 与本目录 [LICENSE](LICENSE)。

发布包包含运行所需的派生知识包，但不包含上游原文压缩包或原始源文件；该知识包的再分发已获权利人授权。上游署名、固定提交和授权说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
