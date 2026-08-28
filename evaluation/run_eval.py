import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ai_generator import generate_ai_variants


cases = json.loads(
    Path("evaluation/eval_cases.json").read_text(encoding="utf-8")
)

results = []

for case in cases:
    print(f"Generating: {case['id']}...")

    result = generate_ai_variants(
        case["title"],
        case["content"],
    )

    results.append(
        {
            "id": case["id"],
            "variants": [
                variant.model_dump()
                for variant in result.variants
            ],
            "usage": result.usage.model_dump(),
        }
    )

Path("evaluation/eval_results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nSaved: evaluation/eval_results.json")