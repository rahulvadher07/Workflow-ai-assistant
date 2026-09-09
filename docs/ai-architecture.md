# AI Architecture

The AI assistant is intentionally deterministic at its execution boundary. Groq is used for model interaction, while routing policy and backend tools provide controlled execution.

## Routing and execution

`backend/ai/agent_rules.json` is the declarative routing-policy catalog. `rule_contract.py` validates its structural contract, `rule_engine.py` evaluates applicable rules, and `orchestrator.py` coordinates the request lifecycle.

The tool registry maps canonical tool names to existing Django-backed implementations in `backend/ai/tools/`. These implementations enforce authoritative scope, permissions, status rules, balance/date rules, duplicate/overlap checks, transactions, and database writes.

## Confirmation

Protected actions declare that confirmation is required. Confirmation phrases are centralized in the catalog's confirmation policy. Execution uses the frozen pending tool name and arguments associated with the authenticated user and immediately preceding turn.

## Knowledge & Policy

PDF content is represented by indexed `KnowledgeChunk` rows. Retrieval can use hybrid semantic and lexical ranking when semantic model support is enabled; otherwise it falls back to deterministic lexical ranking. Retrieved policy content is treated as evidence rather than executable instructions.

## Health checks

The `ai_healthcheck` management command validates the rule/tool catalog, database connectivity, provider configuration, and Knowledge & Policy indexing/semantic availability.
