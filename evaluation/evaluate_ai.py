import json
import sys
from pathlib import Path

from app.services.validator import ValidationError, validate_variant_constraints

PLATFORMS = {"x", "linkedin", "telegram"}


def evaluate_case(case: dict, result: dict) -> dict:
    variants = result.get("variants", [])
    checks = {
        "exactly_three_variants": len(variants) == 3,
        "all_platforms_present": {v.get("platform") for v in variants} == PLATFORMS,
        "valid_structured_fields": all(
            isinstance(v.get("platform"), str)
            and isinstance(v.get("tone"), str)
            and isinstance(v.get("content"), str)
            and isinstance(v.get("hashtags"), list)
            for v in variants
        ),
    }

    constraint_errors = []
    for variant in variants:
        try:
            validate_variant_constraints(
                variant["platform"], variant["content"], variant["tone"]
            )
        except (ValidationError, KeyError, TypeError) as exc:
            constraint_errors.append(str(exc))

    checks["platform_constraints_pass"] = not constraint_errors

    source = case["content"]
    checks["source_content_present"] = bool(source.strip())

    return {
        "id": case["id"],
        "checks": checks,
        "passed": all(checks.values()),
        "constraint_errors": constraint_errors,
        "usage": result.get("usage", {}),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python evaluation/evaluate_ai.py <cases.json> <results.json>")
        return 2

    cases = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    results = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

    by_id = {item["id"]: item for item in results}
    evaluations = [evaluate_case(case, by_id[case["id"]]) for case in cases]

    total = len(evaluations)
    passed = sum(item["passed"] for item in evaluations)
    print(f"Cases: {total}")
    print(f"Passed: {passed}/{total}")
    print(f"Pass rate: {(passed / total * 100):.1f}%" if total else "Pass rate: 0.0%")

    for item in evaluations:
        status = "PASS" if item["passed"] else "FAIL"
        print(f"{status} {item['id']}")
        for name, value in item["checks"].items():
            print(f"  - {name}: {value}")
        if item["constraint_errors"]:
            for error in item["constraint_errors"]:
                print(f"  - error: {error}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
