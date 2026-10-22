# Generic Pre-Tool Hook

`pre_tool_hook.py` is an Agent-neutral pre-execution hook for side-effecting tools. It is installed once by the Agent adapter; users do not configure individual operations.

`agent_pre_tool_hook.py` is the host-facing adapter for hook systems that pass `tool_name`, `tool_input` and `tool_call_id`. It canonicalizes the tool call, looks up the matching POL2 operation by `session + tool_call_id`, consumes the existing permit, and falls back to a full operation decision only when no proxy-issued record exists.

Host environment for this adapter:

```text
POL2_SERVICE_URL=http://127.0.0.1:18080
POL2_HOOK_CLIENT=<same client id used by the model proxy>
POL2_HOOK_ACCOUNT=<same account scope>
POL2_HOOK_SESSION=<same session id>
```

Operators configure these once in the adapter; individual users do not pass tokens or approve each tool call manually.

The host calls it before commands, file writes, deployments, messages or deletions. The hook:

There are two paths:

1. **Preferred: proxy-issued permit.** When the model returns a tool call, the model proxy checks the tool call with the user's task and authorization context and records a one-time permit keyed to the tool-call ID. If the host preserves `pol2.permit` metadata, the hook consumes it directly. If the host strips metadata, the hook derives the stable request ID from `session + tool_call_id`, looks up the same operation record and consumes its permit. Neither path asks the governance model to decide again.
2. **Fallback: direct tool call.** For a tool invocation that did not pass through the model proxy and has no proxy-issued record, the hook sends the tool name, arguments and host context to POL2 for a full operation decision, then consumes the permit.

In both paths the hook stops on `clarify`, `revise`, `reject`, an unavailable service or a replayed permit. `allow_with_conditions` is blocked until the host declares and supplies condition evidence.

Preferred tool-call shape (permit fields are added by the proxy):

```json
{
  "id": "call-1",
  "type": "function",
  "function": {"name": "shell", "arguments": "{\"command\":\"rm /workspace/a.txt\"}"},
  "pol2": {
    "decision": "allow",
    "request_id": "chat-...:tool:0:...",
    "permit": {"token": "..."}
  }
}
```

Example direct event:

```json
{
  "tool_name": "shell",
  "arguments": {"command": "ls -la"},
  "tool_call_id": "call-1",
  "client_id": "agent",
  "account_scope": "local",
  "session_id": "session-1",
  "task_id": "task-...",
  "run_id": "run-...",
  "context": {"cwd": "/workspace"}
}
```

Run:

```bash
python hooks/pre_tool_hook.py < event.json
```

Exit code `0` means the permit was consumed and execution may proceed. Any other result must block execution. The host must fail closed if the hook cannot be executed.

The generic adapter has been exercised end to end with one host integration. Every additional host still needs its adapter installed once and its coverage level accepted separately.
