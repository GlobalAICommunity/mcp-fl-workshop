"""Validate workshop links and the Global AI Learn content contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_TARGET = re.compile(r"\[[^]]*]\(([^)]+)\)")
QUESTION_TYPES = {"single-choice", "multiple-choice", "true-false"}


def load_document(path: Path, errors: list[str]) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    relative = path.as_posix()
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append(f"{relative}: UTF-8 BOM is not allowed")
    if b"\r\n" in raw:
        errors.append(f"{relative}: Learn content must use LF line endings")

    text = raw.decode("utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{relative}: missing opening YAML front matter")
        return {}, text
    try:
        front_matter, body = text[4:].split("\n---\n", 1)
    except ValueError:
        errors.append(f"{relative}: missing closing YAML front matter")
        return {}, text

    data = yaml.safe_load(front_matter)
    if not isinstance(data, dict):
        errors.append(f"{relative}: front matter must be a mapping")
        return {}, body
    return data, body


def validate_questions(path: Path, questions: Any, errors: list[str]) -> None:
    if not isinstance(questions, list) or not questions:
        errors.append(f"{path.as_posix()}: at least one question is required")
        return

    question_ids: set[str] = set()
    for question in questions:
        question_id = question.get("id") if isinstance(question, dict) else None
        if not isinstance(question_id, str) or not SLUG.fullmatch(question_id):
            errors.append(f"{path.as_posix()}: invalid question id {question_id!r}")
            continue
        if question_id in question_ids:
            errors.append(f"{path.as_posix()}: duplicate question id {question_id!r}")
        question_ids.add(question_id)

        question_type = question.get("type")
        if question_type not in QUESTION_TYPES:
            errors.append(f"{path.as_posix()}: invalid type for {question_id!r}")
        options = question.get("options")
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f"{path.as_posix()}: {question_id!r} needs two options")
            continue
        option_ids = [option.get("id") for option in options if isinstance(option, dict)]
        correct = question.get("correctOptionIds")
        if len(option_ids) != len(options) or len(set(option_ids)) != len(option_ids):
            errors.append(f"{path.as_posix()}: invalid option ids for {question_id!r}")
        if not isinstance(correct, list) or not correct or not set(correct) <= set(option_ids):
            errors.append(f"{path.as_posix()}: invalid correctOptionIds for {question_id!r}")
        if question_type in {"single-choice", "true-false"} and len(correct or []) != 1:
            errors.append(f"{path.as_posix()}: {question_id!r} needs one correct option")
        if question_type == "true-false" and len(options) != 2:
            errors.append(f"{path.as_posix()}: {question_id!r} needs exactly two options")


def validate_learn(repo_root: Path, errors: list[str]) -> None:
    course_root = repo_root / "global-ai-learn" / "mcp-workshop"
    course_path = course_root / "course.md"
    course, _ = load_document(course_path, errors)
    if course.get("schemaVersion") != 1:
        errors.append("course.md: schemaVersion must be 1")
    if course.get("durationMinutes") != 90:
        errors.append("course.md: durationMinutes must be 90")

    modules = course.get("modules")
    if not isinstance(modules, list):
        errors.append("course.md: modules must be a list")
        return

    lesson_minutes = 0
    module_root = course_root / "modules"
    for order, module_id in enumerate(modules, start=1):
        matches = list(module_root.glob(f"*-{module_id}"))
        if len(matches) != 1 or not SLUG.fullmatch(str(module_id)):
            errors.append(f"course.md: module {module_id!r} does not resolve uniquely")
            continue
        module_path = matches[0] / "module.md"
        module, _ = load_document(module_path, errors)
        if module.get("id") != module_id or module.get("order") != order:
            errors.append(f"{module_path.as_posix()}: module identity or order mismatch")
        validate_questions(module_path, module.get("questions"), errors)

        pages = module.get("pages")
        if not isinstance(pages, list):
            errors.append(f"{module_path.as_posix()}: pages must be a list")
            continue
        for page_order, page_id in enumerate(pages, start=1):
            page_matches = list((matches[0] / "pages").glob(f"*-{page_id}.md"))
            if len(page_matches) != 1 or not SLUG.fullmatch(str(page_id)):
                errors.append(f"{module_path.as_posix()}: page {page_id!r} does not resolve")
                continue
            page, _ = load_document(page_matches[0], errors)
            if page.get("id") != page_id or page.get("order") != page_order:
                errors.append(f"{page_matches[0].as_posix()}: page identity or order mismatch")
            minutes = page.get("estimatedMinutes")
            if not isinstance(minutes, int) or minutes <= 0:
                errors.append(f"{page_matches[0].as_posix()}: invalid estimatedMinutes")
            else:
                lesson_minutes += minutes

    final_path = course_root / "final-test.md"
    final_test, _ = load_document(final_path, errors)
    validate_questions(final_path, final_test.get("questions"), errors)
    if lesson_minutes != 83:
        errors.append(f"Learn lesson pages total {lesson_minutes} minutes, expected 83")


def validate_links(repo_root: Path, errors: list[str]) -> None:
    paths = [
        repo_root / "README.md",
        *(repo_root / "docs").glob("*.md"),
        *(repo_root / "global-ai-learn" / "mcp-workshop").rglob("*.md"),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_TARGET.findall(text):
            target = target.split(maxsplit=1)[0].strip("<>")
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            target_path = (path.parent / target.split("#", 1)[0]).resolve()
            if not target_path.exists():
                errors.append(f"{path.relative_to(repo_root).as_posix()}: broken link {target!r}")


def validate_repository(repo_root: Path) -> list[str]:
    errors: list[str] = []
    validate_learn(repo_root, errors)
    validate_links(repo_root, errors)
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    errors = validate_repository(repo_root)
    if errors:
        print("Content validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Content validation passed: Learn schema, 83-minute lessons, and local links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
