---
name: pytorch_log_debug
description: Use when the user uploads PyTorch training logs or asks about CUDA OOM, checkpoint loading failure, loss NaN, shape mismatch, dtype, or device errors.
tools:
  - file_reader
  - log_parser
  - python_executor
status: active
trigger: PyTorch error, CUDA OOM, checkpoint error, loss nan, shape mismatch, training log
---

# PyTorch Log Debug Skill

## Purpose

Diagnose PyTorch training failures from logs, stack traces, and experiment configuration.

## Steps

1. Inspect the last error stack and the final training lines.
2. Check CUDA device visibility, memory usage, dtype, tensor shape, and checkpoint path.
3. Identify the likely root cause.
4. Give a minimal fix and a validation step.
5. If the fix is successful, write a reflection memory for future similar tasks.

## Safety

Do not execute user scripts automatically. Request explicit approval before running code.
