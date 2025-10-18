# Company Coding Standards

## 1) Editor Settings
- **Font size**: 16px  
- **Font**: Hack (monospaced, recommended)  
- **Indentation**: Spaces, 4 spaces per indent level  
- **Encoding**: UTF-8  
- **End of line**: LF (Unix-style)  
- **Autosave**: Enabled with 1000 ms delay

### 1.1) Excluded Files and Folders
- **System files**: `.git`, `.svn`, `.hg`, `CVS`, `.DS_Store`  
- **Service folders**: `bin`, `obj`, `node_modules`  
- **Internal Git objects**: `.git/objects/**`

> Note: Do not commit generated artifacts, local IDE settings, or build
> outputs.

---

## 2) Language & Localization
- **Team communication**: Russian  
- **Code & documentation (comments, XML docs, logs)**: English  
- **Error messages (user- and system-facing)**: English (universality)  
- **User interface copy**: Russian  
- **`plan.md` notes**: Russian

---

## 3) Code Quality
- Write clean, maintainable, and efficient code following best practices.
- Adhere to SOLID, DRY, KISS, YAGNI, and DIE principles.
- Follow the conventions of the chosen language and framework.
- Include appropriate comments and documentation where they add clarity.
- Keep classes/methods focused on a single responsibility.

---

## 4) Security
- Never introduce known security vulnerabilities (SQL injection, XSS,
  CSRF, etc.).
- Validate and sanitize all user inputs.
- Use parameterized queries for DB operations.
- Implement proper authentication and authorization.
- Follow least-privilege principles.
- Never store secrets in code or VCS; use a secure secrets manager.
- Use secure transport (HTTPS/TLS) for all network traffic.

---

## 5) Error Handling & Validation
- Implement comprehensive error handling with actionable messages.
- Log errors with sufficient context (correlation IDs, user/session,
  inputs).
- Validate all inputs at system boundaries.
- Use custom exception types where appropriate.
- Provide a global exception handler with safe fallbacks and structured
  logs.

---

## 6) Performance
- Optimize DB access (avoid N+1 queries; prefer joins/explicit loading).
- Use `async/await` for I/O-bound operations.
- Introduce caching where appropriate with clear invalidation rules.
- Choose efficient data structures and algorithms.
- Implement pagination/streaming for large datasets.
- Monitor and optimize memory usage.
- Consider concurrency/parallelism where it is safe and beneficial.

---

## 7) Documentation
- Document all public APIs (XML/Docstrings) including params/returns.
- Document possible exceptions and error codes.
- Keep `README` files up to date with setup/run instructions.
- Record architectural decisions (ADRs) with context and consequences.
- Maintain up-to-date API documentation (Swagger/OpenAPI).
- Provide code examples for complex behaviors.

---

## 8) Testing
- Write unit tests for business logic; target **> 80% coverage** as a
  guideline.
- Follow FIRST principles (Fast, Independent, Repeatable, Self-validating,
  Timely).
- Use test doubles (mocks/stubs) for external dependencies.
- Include integration tests for critical paths.
- Provide end-to-end tests for key user scenarios.
- Cover edge cases and failure modes.
- Keep tests deterministic and isolated.

---

## 9) Python Standards (PEP 8–aligned)
- **Line length**:  
  - **Code**: **79 characters max**  
  - **Comments & docstrings**: **72 characters max**
- **Indentation**: 4 spaces; never use tabs.
- **Naming**:  
  - Modules/packages: `lowercase_with_underscores`  
  - Functions/variables: `lowercase_with_underscores`  
  - Classes/Exceptions: `CapWords`  
  - Constants: `UPPER_CASE_WITH_UNDERSCORES`
- **Imports**: One per line; standard library → third-party → local, each
  in blocks; absolute imports preferred; put imports at top of file.
- **Whitespace**: Follow PEP 8 around operators, commas, slices; no
  trailing spaces; one newline at EOF.
- **Docstrings**: Use triple quotes; describe purpose, params, returns,
  raises; prefer Google or reST style consistently per repo.
- **Typing**: Use type hints; run type checks (e.g., `mypy`) when
  applicable.
- **Errors**: Raise specific exceptions; avoid bare `except`; use
  `finally`/context managers to release resources.
- **Mutability**: Prefer immutability where practical; avoid surprising
  side effects.
- **Logging**: Use `logging` module; no prints in library code.
- **Structure**: Keep functions small and cohesive; avoid deep nesting.

---

## 10) C# Modern Practices
- Use contemporary C# features (records, pattern matching, `async`
  streams).
- Prefer immutability; leverage `record` and `init`-only setters where
  appropriate.
- Use LINQ effectively; avoid multiple enumerations of expensive
  sequences.
- Dispose resources correctly (`using`/`await using`, `IAsyncDisposable`).
- Use expression-bodied members when it improves clarity.
- Enable and respect **nullable reference types**; annotate APIs.
- Use **file-scoped namespaces**.
- Keep `async` all the way; avoid blocking calls on async code.

---

## 11) API Development
- Follow RESTful design principles.
- Implement **API versioning**.
- Use proper HTTP methods and status codes.
- Apply HATEOAS where it adds value and consistency.
- Use DTOs for request/response models; do not expose domain entities
  directly.
- Implement content negotiation and explicit media types.
- Document endpoints with **Swagger/OpenAPI** and keep them current.
- Enforce authentication/authorization (e.g., OAuth2/OIDC) and rate
  limiting where needed.
- Ensure idempotency for safe/retryable operations.

---

## 12) Code Review Guidelines
- Provide constructive, actionable feedback; focus on maintainability and
  correctness.
- Check for security issues and data handling risks.
- Verify adequate test coverage and test quality.
- Ensure adherence to project standards and style.
- Look for performance pitfalls and unnecessary complexity.
- Review error handling and logging quality.
- Confirm sufficient documentation and clear commit history.

---

## 13) Commit Practices
- Write clear, descriptive messages in **English**.
- Follow **Conventional Commits** (`feat:`, `fix:`, `docs:`, `refactor:`,
  `test:`, etc.; optional scope).
- Reference issue IDs where applicable.
- Keep commits atomic and focused.
- **Subject line**: ~50 chars max; blank line; **body** wrapped at ~72
  chars explaining what/why.
- Include type and scope in the subject when meaningful.

---

## 14) Knowledge Sharing
- Add explanations for complex implementations and non-obvious decisions.
- Link to relevant documentation and references.
- Record significant design choices in ADRs.
- Share knowledge via reviews, pair programming, and internal talks.
- Keep onboarding and training materials current.

---

### Appendix A — Compatibility Notes with PEP 8
- Indentation (4 spaces), encoding (UTF-8), and LF line endings align
  with cross-platform tooling and Python norms.  
- Max line lengths are explicitly set to **79 (code)** and **72
  (comments/docstrings)** per PEP 8.  
- Naming, imports ordering, whitespace rules, and docstring guidance
  conform to PEP 8.  
- Logging, exceptions, and resource management recommendations align with
  Python best practices.  

> Non-Python sections (e.g., C# practices) are language-specific and do
> not conflict with PEP 8. For multi-language repos, enforce
> language-specific linters/formatters (e.g., `ruff`/`flake8` + `black`
> with `line-length = 79`, `dotnet format`) via CI.
