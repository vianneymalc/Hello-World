# CLAUDE.md

This file provides guidance for AI assistants (such as Claude) working with this repository.

## Project Overview

**Hello-World** is a personal learning repository created by Vianney Maldonado (@vianneymalc) in July 2016. It was created as a first GitHub project to practice version control workflows.

- **Purpose:** Learning/practice repository
- **Current state:** Minimal — contains only a README and this file
- **No production code, tests, build system, or CI/CD configuration exists yet**

## Repository Structure

```
Hello-World/
├── CLAUDE.md       # This file — guidance for AI assistants
└── README.md       # Project introduction and description
```

## Git Conventions

- **Default branch:** `master`
- **Remote:** `origin` (GitHub — vianneymalc/Hello-World)
- Commit messages should be concise and descriptive (imperative mood, e.g. "Add README" not "Added README")
- Feature branches should be created from `master` and merged via pull request

## Development Workflows

Since this repository currently has no source code, there are no build, test, or lint steps to run. If code is added in the future:

1. Create a feature branch from `master`
2. Make changes with clear, atomic commits
3. Open a pull request to merge into `master`

## Notes for AI Assistants

- This is an empty/learning project — do not assume any frameworks, languages, or tooling are in use unless explicitly added
- Before adding any code or configuration, confirm the intended language and framework with the user
- Keep changes minimal and focused; avoid scaffolding large amounts of boilerplate without instruction
- If a build system, test runner, or linter is introduced, update this file to document the relevant commands
