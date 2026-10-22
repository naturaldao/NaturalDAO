# OpenAI-Compatible Agent Adapter

This document defines the generic model-request adapter contract. It applies to any Agent that can use an OpenAI-compatible endpoint. Product names do not form part of the core contract.

## 1. Model request path

Point the Agent's model base URL at the POL2 service `/v1` endpoint.

In authenticated or multi-workspace mode, these platform fields identify the calling scope:

- `X-POL2-Account`: caller workspace or account scope supplied by the integrating host;
- `X-POL2-Session`: conversation or execution session identifier;
- `X-POL2-Client`: optional adapter identifier;
- `X-POL2-Project`: optional project identifier;
- `X-POL2-Request-Id`: optional stable request identifier for retries.
- `X-POL2-Task`, `X-POL2-Run`, `X-POL2-Step`: optional task-scoped execution identifiers.

Platform fields are used for routing, deduplication and data isolation. They are not POL2 ethical criteria and must not change the decision for identical content and context. When task identifiers are supplied, the model-request adapter checks the step against an active task permit rather than treating every call as a new task.

Local simple mode supplies a fixed local account and session, so headerless requests are accepted. The service must still bind to loopback in that mode. Remote or multi-user deployments must enable authentication and supply real scope fields.

## 2. Current behavior

- The proxy checks input, upstream output and returned tool calls;
- blocked or revised output is returned in the response body as a structured `pol2` decision rather than a transport failure; the current pilot also sets `finish_reason=content_filter`, so hosts must render the governance decision and must not suggest switching models to bypass it;
- streaming is currently buffered until governance completes;
- model input/output coverage alone is `partial`; it does not enforce direct filesystem, shell, deployment or messaging tools.

Task lifecycle APIs are available through `POST /v1/tasks`, task step submission, final delivery checks and `GET /v1/tasks/{id}/timeline`. Adapters that cannot create and track a task should explicitly report request-level governance only.

## 3. Required operation adapter

An Agent that executes side effects must call the operation gate before performing the action, with:

- task, run and step identifiers;
- tool name and arguments;
- project and task context;
- request identifier that is stable across retries.

The service canonicalizes the tool call into the operation content, scope and content hash used by the permit. A client that cannot supply the real tool call and its arguments cannot claim operation coverage.

After execution, the adapter must retain an execution receipt containing exit status, affected objects, output hash and timestamps. The current preview does not yet expose a dedicated receipt endpoint; until it does, adapters must keep that record in their own audit path and submit the actual result through the delivery check. A client that cannot supply an execution receipt cannot claim full governance.

## 4. Required artifact adapter

Before publishing or delivering a file, code change, webpage, message or report, the adapter must submit the actual artifact version for result check. The checked version must be the delivered version. Any modification invalidates the release record.

## 5. Presentation adapter

The service returns structured governance decisions. A client may render task cards, gate cards, delivery cards and exception cards through its own UI.

Cards must not be appended to code, JSON, markdown artifacts or message bodies that are treated as deliverable content.

## 6. Coverage declaration

Every adapter must declare one of:

- `full`: model, operation, artifact and presentation adapters installed and tested;
- `partial`: only some control points are installed;
- `audit_only`: decisions are logged but side effects are not blocked;
- `unsupported`: the client cannot be governed.

The adapter must state which fields and controls it actually supports. Product names alone do not establish a coverage level.

## 7. Reference adapter

Any concrete reference adapter is replaceable and must not become a core dependency.
