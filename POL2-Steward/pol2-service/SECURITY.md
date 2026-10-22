# Security Policy

## Reporting

Do not open a public issue containing credentials, private data or an unpatched bypass. Report security concerns privately to the repository owner.

## Repository rules

- Never commit `.env`, service tokens, model keys, database passwords, identity keys, dumps, logs or backups.
- Do not weaken fail-closed behavior to work around an unavailable dependency.
- Treat governance decisions, permits and audit events as security-sensitive data.
- Adapters claiming `full` coverage must prove operation and artifact enforcement, not only model proxying.
