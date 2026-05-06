import re
from typing import Any


ERROR_PATTERNS = [
    r"Traceback \(most recent call last\)",
    r"CUDA out of memory",
    r"RuntimeError:[^\n]+",
    r"ValueError:[^\n]+",
    r"TypeError:[^\n]+",
    r"ModuleNotFoundError:[^\n]+",
    r"ImportError:[^\n]+",
    r"FileNotFoundError:[^\n]+",
    r"PermissionError:[^\n]+",
    r"shape mismatch",
    r"size mismatch",
    r"nan loss",
    r"checkpoint loading failed",
]

KEYWORD_PATTERNS = {
    "OOM": [r"out of memory", r"\boom\b", r"cuda.*memory"],
    "NaN": [r"\bnan\b", r"nan loss", r"loss is nan"],
    "shape": [r"shape mismatch", r"size mismatch", r"mat1 and mat2", r"expected.*shape"],
    "dtype": [r"dtype", r"float16", r"float32", r"bfloat16", r"half", r"double"],
    "device": [r"device", r"cuda", r"cpu", r"same device"],
    "checkpoint": [r"checkpoint", r"state_dict", r"load_state_dict", r"missing key", r"unexpected key"],
    "permission": [r"permission denied", r"permissionerror"],
    "module not found": [r"modulenotfounderror", r"no module named", r"importerror"],
}

FILE_LINE_PATTERN = re.compile(r'File "([^"]+)", line (\d+)(?:, in ([^\n]+))?')


def parse_log_text(text: str, tail_lines: int = 80) -> dict[str, Any]:
    lines = text.splitlines()
    tail = lines[-tail_lines:] if tail_lines > 0 else lines
    normalized = text.lower()

    error_type = extract_error_type(text)
    file_references = extract_file_references(text)
    keywords = extract_keywords(normalized)

    return {
        "tail_lines": tail,
        "tail_text": "\n".join(tail),
        "error_type": error_type,
        "file_references": file_references,
        "keywords": keywords,
        "line_count": len(lines),
    }


def extract_error_type(text: str) -> str | None:
    for pattern in ERROR_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(0).strip()
            if ":" in value and not value.lower().startswith("file "):
                return value.split(":", 1)[0].strip()
            return value
    last_exception = re.findall(r"([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))(?::[^\n]*)?", text)
    return last_exception[-1] if last_exception else None


def extract_file_references(text: str) -> list[dict[str, Any]]:
    references = []
    for match in FILE_LINE_PATTERN.finditer(text):
        references.append(
            {
                "path": match.group(1),
                "line": int(match.group(2)),
                "function": (match.group(3) or "").strip(),
            }
        )
    return references[-8:]


def extract_keywords(normalized_text: str) -> list[str]:
    found = []
    for keyword, patterns in KEYWORD_PATTERNS.items():
        if any(re.search(pattern, normalized_text, flags=re.IGNORECASE) for pattern in patterns):
            found.append(keyword)
    return found


def diagnose_from_parsed_log(parsed: dict[str, Any]) -> dict[str, list[str] | str]:
    keywords = set(parsed.get("keywords", []))
    error_type = parsed.get("error_type") or "Unknown error"
    causes: list[str] = []
    steps: list[str] = []
    fixes: list[str] = []
    missing_info: list[str] = []

    if "OOM" in keywords:
        causes.append("GPU memory is likely exhausted by batch size, sequence length, activation storage, or data prefetching.")
        steps.extend(
            [
                "Check the exact GPU memory line and current batch size.",
                "Confirm whether evaluation, gradient accumulation, or dataloader workers increased memory pressure.",
                "Inspect recent model/input size changes before the failure.",
            ]
        )
        fixes.extend(
            [
                "Reduce batch size or sequence/image resolution first.",
                "Enable gradient accumulation, mixed precision, activation checkpointing, or clear unused tensors between phases.",
                "Restart the process if memory is held by a stale run.",
            ]
        )

    if "NaN" in keywords:
        causes.append("Training became numerically unstable, commonly from learning rate, loss scaling, invalid data, or unsafe operations.")
        steps.extend(
            [
                "Locate the first step where loss becomes NaN instead of only the final traceback.",
                "Check input batches for NaN/Inf and labels outside the expected range.",
                "Log gradient norm and learning rate around the failure.",
            ]
        )
        fixes.extend(
            [
                "Lower learning rate and add gradient clipping.",
                "Guard divisions/log/sqrt operations with eps values.",
                "Disable mixed precision temporarily to confirm whether loss scaling is involved.",
            ]
        )

    if "shape" in keywords:
        causes.append("Tensor shapes or checkpoint parameter shapes do not match the model expectation.")
        steps.extend(
            [
                "Print the shapes immediately before the failing operation.",
                "Compare model output shape, target shape, and loss function requirements.",
                "If loading a checkpoint, compare saved parameter shapes with the current model definition.",
            ]
        )
        fixes.extend(
            [
                "Adjust reshape/permute/view logic or batch dimension handling.",
                "Use the correct head/class count for the checkpoint.",
                "Load checkpoints with strict=False only when missing/unexpected keys are understood.",
            ]
        )

    if "dtype" in keywords:
        causes.append("A tensor dtype mismatch may be feeding an operation that expects another precision or integer label type.")
        steps.append("Print dtype for model inputs, labels, loss inputs, and checkpoint tensors near the failing line.")
        fixes.append("Cast tensors explicitly, for example labels to long for classification loss or inputs to the model precision.")

    if "device" in keywords:
        causes.append("Some tensors or modules may be split across CPU and CUDA devices.")
        steps.append("Print `.device` for model parameters, inputs, labels, and tensors created inside the forward path.")
        fixes.append("Move newly created tensors to the same device as the input or model before use.")

    if "checkpoint" in keywords:
        causes.append("Checkpoint loading likely mismatches path, architecture, key prefix, shape, or framework version.")
        steps.extend(
            [
                "Verify the checkpoint file exists and is readable.",
                "Inspect missing/unexpected keys from load_state_dict.",
                "Confirm the current model config matches the training config used for the checkpoint.",
            ]
        )
        fixes.extend(
            [
                "Use the matching config and model class for the checkpoint.",
                "Strip or add `module.` prefixes when moving between DataParallel/DDP and single-GPU runs.",
                "Use strict=False only for intentionally changed heads or optional modules.",
            ]
        )

    if "permission" in keywords:
        causes.append("The process likely cannot read or write a required file or directory.")
        steps.append("Check the path in the traceback and the current process user permissions.")
        fixes.append("Create the target directory and grant read/write permission, or redirect outputs to a writable path.")

    if "module not found" in keywords:
        causes.append("A required Python package or local module is missing from the active environment or PYTHONPATH.")
        steps.extend(["Confirm the active interpreter/venv.", "Check whether the module is installed or the repo root is on PYTHONPATH."])
        fixes.extend(["Install the missing package in the active environment.", "Run from the project root or set PYTHONPATH correctly."])

    if not causes:
        causes.append("The log does not contain enough known patterns for a confident diagnosis.")
        steps.extend(
            [
                "Provide the full traceback and 50-100 lines before the error.",
                "Include environment details such as framework version, GPU model, command line, and recent code/config changes.",
            ]
        )
        fixes.append("No specific fix can be recommended yet without more context.")

    missing_info.extend(default_missing_info(keywords))
    return {
        "summary": build_summary(error_type, parsed),
        "possible_causes": dedupe(causes),
        "troubleshooting_steps": dedupe(steps),
        "fix_suggestions": dedupe(fixes),
        "need_more_info": dedupe(missing_info),
    }


def default_missing_info(keywords: set[str]) -> list[str]:
    info = ["Full traceback", "Training command/config", "Relevant model/data shapes near the failing line"]
    if "OOM" in keywords:
        info.extend(["GPU model and memory size", "Batch size and input resolution/sequence length"])
    if "checkpoint" in keywords:
        info.extend(["Checkpoint path", "Model config used to create the checkpoint"])
    if "NaN" in keywords:
        info.extend(["Learning rate schedule", "First iteration where loss becomes NaN"])
    return info


def build_summary(error_type: str, parsed: dict[str, Any]) -> str:
    keywords = ", ".join(parsed.get("keywords", [])) or "no known keyword"
    references = parsed.get("file_references", [])
    if references:
        last_ref = references[-1]
        location = f"{last_ref['path']}:{last_ref['line']}"
        return f"{error_type}; detected keywords: {keywords}; last referenced location: {location}."
    return f"{error_type}; detected keywords: {keywords}; no file/line reference was extracted."


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
