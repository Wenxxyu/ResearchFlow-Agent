---
name: repo_understanding
description: Use when the user asks about repository structure, function behavior, code search, module dependencies, implementation mapping, or error location in source code.
tools:
  - code_search
  - file_reader
  - symbol_search
status: active
trigger: code repository, function explanation, module structure, implementation detail, traceback location
---

# Repository Understanding Skill

## Purpose

Help users understand a code repository and connect high-level concepts to concrete source files.

## Steps

1. Summarize the repository directory structure.
2. Search for relevant symbols, filenames, or error messages.
3. Read the smallest useful code region.
4. Explain function behavior and dependencies.
5. Point to files and functions involved in the answer.

## Safety

Do not modify repository files unless the user explicitly asks for code changes.
