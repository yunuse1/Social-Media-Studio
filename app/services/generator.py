from typing import Dict
from app.services.validator import validate_variant_constraints

def generate_platform_variants(title: str, content: str) -> Dict[str, str]:
    clean_text = " ".join(content.split())
    
    short_summary = clean_text[:200] if len(clean_text) > 200 else clean_text
    x_content = f"📢 {title}\n\n{short_summary}...\n\n#Backend #API #Tech"
    
    linkedin_content = (
        f"🚀 **{title}**\n\n"
        f"{clean_text[:1200]}\n\n"
        f"Key Takeaway: Engineering reliable systems requires robust error handling and boundary testing.\n\n"
        f"#SoftwareEngineering #BackendDevelopment #Architecture"
    )
    
    telegram_content = (
        f"📝 *{title}*\n\n"
        f"{clean_text[:800]}\n\n"
        f"🔗 [Read full post] | #Update"
    )

    variants = {
        "x": x_content,
        "linkedin": linkedin_content,
        "telegram": telegram_content
    }

    for platform, text in variants.items():
        validate_variant_constraints(platform, text)

    return variants