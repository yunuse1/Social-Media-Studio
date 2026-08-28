from app.database import get_db, init_db
from app.services.generator import generate_platform_variants


def seed():
    init_db()
    conn = get_db()

    title = "AI in Backend Engineering"
    content = (
        "Artificial intelligence is changing how backend engineers build "
        "reliable and scalable systems. Teams can use AI-assisted tools to "
        "speed up routine development work while keeping review and testing "
        "in the engineering workflow."
    )

    existing = conn.execute(
        "SELECT id FROM posts WHERE title = ? AND content = ? LIMIT 1",
        (title, content),
    ).fetchone()

    if existing:
        print(f"Seed already present: post_id={existing['id']}")
        conn.close()
        return

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO posts (title, content, source_url) VALUES (?, ?, ?)",
        (title, content, None),
    )
    post_id = cursor.lastrowid

    for platform, variant_text in generate_platform_variants(title, content).items():
        cursor.execute(
            "INSERT INTO variants (post_id, platform, content, status) VALUES (?, ?, ?, 'draft')",
            (post_id, platform, variant_text),
        )

    conn.commit()
    conn.close()
    print(f"Seeded post_id={post_id} with X, LinkedIn, and Telegram variants")


if __name__ == "__main__":
    seed()
