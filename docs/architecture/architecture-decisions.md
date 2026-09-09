# Architecture Decisions

## ADR-001: Use a Monorepo

### Status
Accepted

### Decision
The AI Business Employee platform will use a monorepo.

### Reason
The platform will contain multiple applications, backend services,
AI services, workers, shared packages, infrastructure, and documentation.

A monorepo allows these components to be maintained in a single
repository while sharing code and configuration.

### Alternatives Considered
- Multiple repositories
- Monorepo

### Decision
Use a monorepo.








## ADR-002: Use GitHub

### Status
Accepted

### Decision
GitHub will host the project's Git repository.

### Reason
GitHub provides version control hosting, pull requests,
CI/CD integration, issue tracking, and collaboration capabilities.
