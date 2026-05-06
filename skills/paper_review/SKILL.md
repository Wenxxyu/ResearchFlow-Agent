---
name: paper_review
description: Use when the user asks about paper reading, method summary, novelty, experiments, limitations, or citation-grounded QA.
tools:
  - paper_parser
  - hybrid_retriever
  - citation_verifier
status: active
trigger: paper PDF, research paper summary, method comparison, experiment setting, cited answer
---

# Paper Review Skill

## Purpose

Help users understand research papers with grounded evidence and citations.

## Steps

1. Identify the user question type: summary, method, experiment, limitation, or comparison.
2. Retrieve relevant chunks from the project knowledge base.
3. Prefer evidence from abstract, method, experiment, and conclusion sections.
4. Generate a concise answer with citation markers.
5. Verify every important claim has a source citation.

## Safety

Do not fabricate paper claims that are not supported by retrieved evidence.
