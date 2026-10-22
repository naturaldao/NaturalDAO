# POL2 Steward

**Knowledge-grounded governance for POL2.** POL2 Steward (POL2 治理管家) is an Agent-neutral governance proxy for evaluating requirements, execution steps, tool operations and final artifacts against a versioned ethical framework.

**Status: developer preview. Not production-approved.** The repository contains a working service core, task-level governance APIs, a reproducible offline knowledge package and automated tests. Production hardening described in the roadmap is still in progress.

## Architecture

```text
Agent
  -> model request adapter
  -> POL2 task and step governance
  -> operation / artifact adapters
  -> structured decisions, permits, card events and audit timeline
```

The core does not depend on a specific Agent, UI or hosting platform. Client-specific integrations are adapters.

## Repository layout

```text
docs/          Public design, implementation and production roadmap
pol2-service/  Service code, tests, knowledge data and build tools
```

## Quick start

```bash
cd pol2-service
./install.sh
./start.sh
```

`install.sh` creates the Python environment, installs dependencies, starts a bundled PostgreSQL/pgvector container and prefills the default model endpoint and model name. In the normal case the user only enters an API key. Requirements are Python 3.10+ and Docker with the compose plugin. The prebuilt runtime knowledge package is bundled; users do not need to download or compile the theory package.

Then configure the Agent's OpenAI-compatible model base URL as:

```text
http://127.0.0.1:18080/v1
```

No additional Agent-specific proxy header is required in local simple mode. See [pol2-service/README.md](pol2-service/README.md) and the [Agent integration guide](docs/Agent接入与部署指南-v1.0-20261022.md).

Simple mode is for a single trusted user on the same machine. Keep the service bound to loopback; remote or multi-user deployments must enable authentication, HTTPS and network access control.

## Public documents

- [Service Design v1.1](docs/POL2服务流程正式设计-v1.1-20261022.md)
- [Implementation Plan v1.2](docs/POL2服务实施方案-v1.2-20261022.md)
- [Governance Card Contract v1.1](docs/POL2治理卡片定义-v1.1-20261022.md)
- [Production Roadmap v1.1](docs/POL2治理服务生产化路线图-v1.1-20261022.md)
- [Agent Integration and Deployment Guide v1.0](docs/Agent接入与部署指南-v1.0-20261022.md)

## Current guarantees

- Model input, output and returned tool calls are reviewed.
- Tasks, runs, steps, permits, card events and delivery checks are persisted.
- Repeated request IDs with different content are rejected.
- Release permits can be consumed once.
- A generic fail-closed pre-tool hook is included for operation enforcement.
- Tool calls approved by the model proxy are recorded with one-time operation permits keyed to the tool-call ID. The hook resolves and consumes that permit, using embedded metadata when the host preserves it and the stable request record when it does not. Neither path asks the governance model to decide a second time.
- One real Agent adapter has passed an end-to-end engineering acceptance covering an allowed write, a blocked unauthorized deletion, and an explicitly authorized deletion.
- Source files are fetched from a pinned upstream commit and verified by size and SHA-256.
- The full test suite runs from a clean checkout.

## Current limitations

- Some adapters still use the legacy request-level path.
- Risk escalation in the task API currently depends on adapter-provided risk signals and step kinds.
- Operation enforcement is not yet mandatory for every client.
- Card events are persisted, but no standalone presentation adapter is included yet.
- Audit records are not yet an append-only hash chain.
- The knowledge package remains a behavior-verified candidate.
- High availability, certification of every adapter and production model approval are still pending. A single external PostgreSQL deployment has passed engineering acceptance.

See the production roadmap for the remaining gates.

## Security and licensing

Do not commit credentials, private data, deployment records or backups. See [SECURITY.md](pol2-service/SECURITY.md).

The code is released under the MIT License. See [LICENSE](LICENSE); the service directory carries the same license at [pol2-service/LICENSE](pol2-service/LICENSE). MIT applies to the service code, not to third-party theory texts.

The release bundles a derived runtime knowledge package. Redistribution of that package has been authorized by the publisher; upstream attribution and the fixed source commit are recorded in [THIRD_PARTY_NOTICES.md](pol2-service/THIRD_PARTY_NOTICES.md).
