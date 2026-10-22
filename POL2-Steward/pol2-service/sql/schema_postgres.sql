-- Production PostgreSQL schema.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS projects (
  id text PRIMARY KEY, name text NOT NULL, owner_scope text NOT NULL,
  status text NOT NULL DEFAULT 'active', version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  client_id text NOT NULL, account_scope text NOT NULL, session_id text NOT NULL,
  project_id text NOT NULL REFERENCES projects(id), updated_at timestamptz NOT NULL,
  PRIMARY KEY (client_id, account_scope, session_id)
);

CREATE TABLE IF NOT EXISTS requests (
  id text PRIMARY KEY, request_id text NOT NULL UNIQUE,
  client_id text NOT NULL, account_scope text NOT NULL, session_id text NOT NULL,
  project_id text REFERENCES projects(id), stage text NOT NULL,
  input_text text NOT NULL, context_json jsonb NOT NULL,
  input_sha256 text, context_sha256 text, package_id text,
  task_id text, run_id text, step_id text,
  status text NOT NULL, decision_json jsonb, created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
  id text PRIMARY KEY, project_id text, name text NOT NULL, goal text NOT NULL,
  status text NOT NULL, scope_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  conditions_json jsonb NOT NULL DEFAULT '[]'::jsonb, version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id text PRIMARY KEY, task_id text NOT NULL REFERENCES tasks(id),
  status text NOT NULL, created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS steps (
  id text PRIMARY KEY, task_id text NOT NULL REFERENCES tasks(id),
  run_id text NOT NULL REFERENCES runs(id), seq integer NOT NULL,
  kind text NOT NULL, request_id text, input_sha256 text,
  status text NOT NULL, decision_json jsonb, created_at timestamptz NOT NULL, ended_at timestamptz
);

CREATE TABLE IF NOT EXISTS permits (
  id text PRIMARY KEY, request_id text, task_id text, run_id text,
  permit_type text NOT NULL, stage text NOT NULL, subject_sha256 text,
  scope_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  conditions_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  evidence_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  rules_version text, model_version text, status text NOT NULL,
  issued_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, consumed_at timestamptz
);

CREATE TABLE IF NOT EXISTS card_events (
  id text PRIMARY KEY, task_id text NOT NULL REFERENCES tasks(id), run_id text,
  card_type text NOT NULL, decision_json jsonb NOT NULL, created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
  id text PRIMARY KEY, project_id text NOT NULL REFERENCES projects(id),
  source_request_id text, kind text NOT NULL, content text NOT NULL,
  status text NOT NULL, scope text NOT NULL, created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS cache (
  cache_key text PRIMARY KEY, response_json jsonb NOT NULL, expires_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS appeals (
  id text PRIMARY KEY, request_id text NOT NULL, reason text NOT NULL,
  decision_json jsonb, created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id bigserial PRIMARY KEY, request_id text, event_type text NOT NULL,
  task_id text, run_id text, step_id text,
  data_json jsonb NOT NULL, created_at timestamptz NOT NULL
);

-- Optional semantic index for the fixed embedding package.
CREATE TABLE IF NOT EXISTS embeddings (
  record_id text PRIMARY KEY, record_type text NOT NULL,
  embedding halfvec(4096) NOT NULL, embedding_model text NOT NULL,
  indexed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS steps_task_idx ON steps(task_id, seq);
CREATE INDEX IF NOT EXISTS permits_task_idx ON permits(task_id, status);
