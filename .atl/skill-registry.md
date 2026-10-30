# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| FastAPI, Pydantic, async Python, Python API, REST API Python, SQLAlchemy async, JWT authentication, OpenAPI, Swagger Python | fastapi-expert | C:\Users\Mateows\.agents\skills\fastapi-expert\SKILL.md |
| JWT, OAuth2, session management, RBAC | auth-implementation-patterns | C:\Users\Mateows\.agents\skills\auth-implementation-patterns\SKILL.md |
| red-green-refactor, test-first, integration tests | tdd | C:\Users\Mateows\.agents\skills\tdd\SKILL.md |
| When user says "update skills", "skill registry", "actualizar skills", "update registry", or after installing/removing skills | skill-registry | C:\Users\Mateows\.config\opencode\skills\skill-registry\SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### fastapi-expert
- Use type hints everywhere; FastAPI requires them
- Use Pydantic V2 syntax (`field_validator`, `model_validator`, `model_config`) — never V1 (`@validator`, `class Config`)
- Use `Annotated` pattern for dependency injection
- Use async/await for all I/O operations; no synchronous database calls
- Use `X | None` instead of `Optional[X]`
- Return proper HTTP status codes; document endpoints via auto-generated OpenAPI
- Never store passwords in plain text; never hardcode configuration values

### auth-implementation-patterns
- Never store plain passwords; always hash with bcrypt/argon2
- Use short-lived access tokens (15-30 minutes max)
- Use secure cookies: httpOnly, secure, sameSite flags
- Validate all input: email format, password strength
- Rate limit auth endpoints to prevent brute force attacks
- Always validate server-side; never trust client-side auth checks only
- Rotate JWT/session secrets regularly

### tdd
- Red before green: write failing test first, then only enough code to pass
- One slice at a time: one seam, one test, one minimal implementation per cycle
- Refactoring is not part of the loop; belongs to the review stage
- No implementation-coupled tests (mocks internals, private methods)
- No tautological assertions; expected values from independent source of truth
- Work in vertical slices, not horizontal slicing (all tests first)

### skill-registry
- Scan all known skill directories for SKILL.md files
- SKIP sdd-*, _shared, and self (skill-registry) when scanning
- Generate compact rules blocks (5-15 lines) per skill — actionable rules only
- Always write `.atl/skill-registry.md`
- Always save to engram if available (topic_key: skill-registry)
- Add `.atl/` to `.gitignore` if present and not listed

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| — | — | No project-level convention files found (AGENTS.md, CLAUDE.md, .cursorrules, GEMINI.md, copilot-instructions.md) |
