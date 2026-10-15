# ExamSentinel Documentation

Reference documentation for running, operating and extending ExamSentinel. Start with the
[project README](../README.md) for an overview.

## Getting started

| Document | Description |
|---|---|
| [Installation](INSTALLATION.md) | Local setup (one-command or manual), Docker Compose, troubleshooting |
| [Staff guide](STAFF_GUIDE.md) | Building and running exams, proctoring, reviewing, grading, practice problems |

## Reference

| Document | Description |
|---|---|
| [Architecture](ARCHITECTURE.md) | Components, data model and request flow |
| [API reference](API.md) | Practice and code-execution endpoints with real examples |
| [Code execution](CODE_EXECUTION.md) | The sandbox, judge modes, comparison rules, verdicts and limits |
| [Question bank](DSA_QUESTION_BANK.md) | The 127-problem index and how to add problems |

## Operations

| Document | Description |
|---|---|
| [Production readiness](PRODUCTION_READINESS.md) | What the production rehearsal verified, the operator checklist and known limitations |
| [AWS deployment](AWS_DEPLOYMENT.md) | Production deployment on ECS, EC2, RDS, ElastiCache and S3 |
| [Security](SECURITY.md) | Verified security controls, deployment requirements and known gaps |
| [Testing](TESTING.md) | Test suites, how to run them and latest results |

## Contributing

| Document | Description |
|---|---|
| [Contributing](CONTRIBUTING.md) | Workflow, engineering rules and review checklist |

## Planning archive

The [`planning/`](planning/) folder keeps the original product brief, plan, prompt, feature
inventory and E2E test specification written at the start of the project. They are kept for
traceability (some are verified verbatim by tests) and are not maintained as current
documentation.
