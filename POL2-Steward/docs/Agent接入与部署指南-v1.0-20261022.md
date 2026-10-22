# POL2 Agent 接入与部署指南

版本：v1.0  
日期：2026-10-22  
状态：公开预览版，适用于受控环境

## 1. 用户需要完成什么

POL2 不会自动接管机器上的所有 Agent。用户必须把 Agent 的模型请求和执行控制接入 POL2。

接入分为四个控制点：

| 控制点 | 作用 | 缺少后的结果 |
| --- | --- | --- |
| 模型请求适配 | 把模型地址指向 POL2 | 无法治理模型输入/输出 |
| 操作适配 | 副作用工具执行前调用操作检查并消费许可 | 无法阻止命令、文件、发布、删除等操作 |
| 产物适配 | 交付前提交实际文件、代码或报告 | 无法检查最终结果 |
| 展示适配 | 渲染任务卡、门禁卡和交付卡 | 用户看不到治理结果，但后台记录仍存在 |

只接模型代理时，只能声明“部分治理”。

## 2. 准备环境

前置条件：

- Python 3.10 以上；
- 一个 OpenAI 兼容的大语言模型端点和 API key；
- Docker 与 compose 插件；
- 默认由安装脚本启动 PostgreSQL/pgvector；也可以配置外部 PostgreSQL；
- 如服务需要被其他机器访问，应在前面部署 HTTPS 反向代理和网络访问控制。

## 3. 一键安装

```bash
cd pol2-service
./install.sh
```

安装脚本会自动创建 Python 环境、安装依赖、启动 PostgreSQL/pgvector 容器、生成服务密钥，并使用发布包内已经构建好的知识包。普通用户不需要下载理论原文或重新构建知识包。

安装脚本已经预填默认的模型地址和模型名。正常情况只需要输入 API key；使用其他兼容服务时才需要修改地址和模型名：

- OpenAI 兼容的模型地址；
- 模型名称；
- API key。

## 4. 配置一个模型 API

`install.sh` 会将这些配置写入本机 `.env`。也可以预先通过环境变量传入：

```bash
export POL2_LLM_BASE_URL='https://api.example.com/v1'
export POL2_LLM_MODEL='your-model'
export POL2_LLM_API_KEY='replace-with-secret'
./install.sh
```

默认情况下，治理判断和执行模型共用这套配置。需要单独治理模型时，才使用 `POL2_MODEL_BASE_URL`、`POL2_MODEL_NAME` 和 `POL2_MODEL_API_KEY` 覆盖。

开发环境可以使用参考判定器验证流程，但不能把它称为生产模型：

```bash
export POL2_ALLOW_CANDIDATE_PACKAGE='1'
export POL2_ALLOW_REFERENCE_JUDGE='1'
```

生产环境应关闭参考判定器，使用正式知识包、正式模型和不可变密钥。

## 5. 数据库

默认使用 Docker 管理的 PostgreSQL/pgvector，安装脚本会自动启动数据库并初始化表结构。

使用已有 PostgreSQL 时，可在首次安装前提供：

```bash
export POL2_DATABASE_URL='postgresql://user:password@127.0.0.1:5432/pol2'
export POL2_EMBEDDING_DIM='4096'
```

启用向量检索时还要配置：

```bash
export POL2_EMBEDDING_BASE_URL='http://127.0.0.1:11434/v1'
export POL2_EMBEDDING_MODEL='your-embedding-model'
export POL2_EMBEDDING_TIMEOUT='180'
export POL2_REQUIRE_EMBEDDINGS='1'
```

## 6. 启动服务

```bash
./start.sh
```

检查：

```bash
curl http://127.0.0.1:18080/health
```

生产环境如需要跨机器访问，不应直接暴露本端口；应通过受控 HTTPS 入口和网络策略接入。

## 7. 创建项目、任务和运行

创建任务：

```text
POST /v1/tasks
```

请求至少包含：

- 任务名称；
- 目标和验收标准；
- 背景；
- Agent 客户端标识、工作空间和会话标识；
- 可选项目标识。

任务入口会执行完整治理。返回的任务状态可能是：

- `active`：可以直接执行；
- `pending_conditions`：必须补充条件证据后才能激活；
- `needs_input`、`needs_revision`、`rejected`：不能直接执行。

条件满足后调用：

```text
POST /v1/tasks/{task_id}/activate
```

## 8. 接入 Agent 的模型请求

将 Agent 的 OpenAI 兼容模型地址改为：

```text
http://POL2_HOST:18080/v1
```

本地简单模式默认只需要把 Agent 的模型地址改为上面的地址，不需要额外请求头。

需要任务级隔离、多工作空间或远程访问时，可增加：

```text
X-POL2-Client: agent-name
X-POL2-Account: workspace-id
X-POL2-Session: session-id
X-POL2-Task: task-id
X-POL2-Run: run-id
X-POL2-Request-Id: stable-request-id
```

同一个请求重试必须复用同一个请求号；相同请求号携带不同正文会被拒绝。

如果没有 `X-POL2-Task`，服务使用兼容的单请求治理路径；本地简单模式会自动使用本地工作空间和会话。持续任务仍建议创建 Task。

## 9. 接入工具和副作用操作

命令执行、文件写入、安装依赖、发送消息、发布、部署、删除等操作必须在执行前调用：

```text
POST /v1/govern/operation
```

返回允许后，执行端必须消费一次性许可：

```text
POST /v1/permits/consume
```

执行后应保留执行回执、影响对象和输出哈希。当前预览尚未提供独立的执行回执接口，适配器先保存在自身审计路径，并通过最终交付检查提交实际产物。通用 Hook 已实现，并完成一个真实宿主的端到端验收（允许写入、阻止未授权删除、执行明确授权删除）。其他 Agent 仍需安装一次适配器，并单独验收其覆盖等级。

仓库附带一个通用、失败关闭的前置工具 Hook：`hooks/pre_tool_hook.py`。宿主应在每次副作用操作前调用它，只有 Hook 返回 `allow` 才继续执行；服务不可用、许可被消费过或条件未满足时必须阻止操作。

当 tool call 由模型代理返回时，POL2 已经把任务、用户原话中的授权、工具参数和输入决定一起交给治理模型判断，并记录以 tool-call ID 绑定的一次性许可。若宿主保留 `pol2.permit` 元数据，Hook 直接消费该许可；若宿主裁掉元数据，Hook 用 `session + tool_call_id` 推出稳定请求号，回查同一操作记录并消费其许可。两条路径都不会再次调用治理模型。只有完全没有经过模型代理、也不存在代理记录的直接工具调用，才走完整的操作治理回退路径。

### 9.1 本地简单模式的安全边界

`POL2_SIMPLE_MODE=1` 只适合本机、单用户、受控环境。使用简单模式时必须：

- 服务只绑定 `127.0.0.1`，不暴露到局域网或公网；
- 不与不受信任的本地进程共用同一台机器；
- 不把服务地址、令牌或数据库端口转发给外部。

远程访问、多用户或多工作空间部署必须关闭简单模式，启用服务令牌、身份签名、HTTPS 反向代理和网络访问控制。简单模式不是生产部署选项。

## 10. 提交最终交付

最终文件、代码、网页或报告必须提交：

```text
POST /v1/tasks/{task_id}/deliver
```

提交的是实际产物，不是“我准备交付”的说明。产物修改后必须重新检查。

## 11. 查询任务时间线

```text
GET /v1/tasks/{task_id}/timeline
```

时间线包含任务、运行、步骤、许可、卡片事件、请求和审计事件。普通步骤不生成用户卡，只在时间线留痕。

## 12. 验收一个 Agent 是否真正接入

至少完成：

1. 模型请求确实经过 POL2 地址；
2. 任务能够创建、激活并生成任务卡；
3. 普通步骤进入步骤时间线；
4. 高风险操作在执行前被阻止或升级；
5. 许可只能消费一次；
6. 最终交付检查的是实际产物；
7. 任务时间线能串起请求、决定和产物；
8. 断开 POL2 后 Agent 不应绕过治理继续执行高风险操作。

只完成第 1 项时，应标注为部分治理。
