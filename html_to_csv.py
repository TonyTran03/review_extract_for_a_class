import csv
import re
from pathlib import Path

from bs4 import BeautifulSoup


HTML_DIR = Path("review_pages")
OUTPUT_FILE = Path("reviews.csv")
REVIEW_SELECTOR = 'p[class*="comment__"]'
DATE_RE = re.compile(
    r"^(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},\s+\d{4}$"
)


def text(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def parse_page(path: Path) -> list[dict[str, str | int]]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    page_match = re.search(r"(\d+)", path.stem)
    page_number = int(page_match.group(1)) if page_match else 0
    rows = []

    for comment in soup.select(REVIEW_SELECTOR):
        container = comment.find_parent("li") or comment.parent

        author_links = container.select('a[href*="/user_details"]')
        author_link = next((link for link in author_links if text(link)), None)
        rating_node = container.select_one('[role="img"][aria-label*="star rating"]')

        rating = ""
        if rating_node:
            match = re.search(r"([0-5](?:\.\d+)?)\s+star", rating_node.get("aria-label", ""))
            rating = match.group(1) if match else ""

        date = next(
            (
                candidate
                for node in container.find_all(["span", "p"])
                if DATE_RE.fullmatch(candidate := text(node))
            ),
            "",
        )

        rows.append(
            {
                "page": page_number,
                "offset": max(0, (page_number - 1) * 10),
                "reviewer": text(author_link),
                "rating": rating,
                "date": date,
                "review": text(comment),
                "reviewer_url": author_link.get("href", "") if author_link else "",
                "source_file": path.name,
            }
        )

    return rows


def main() -> None:
    paths = sorted(HTML_DIR.glob("*.html"))
    if not paths:
        raise SystemExit(f"No HTML files found in {HTML_DIR.resolve()}")

    rows = []
    for path in paths:
        page_rows = parse_page(path)
        rows.extend(page_rows)
        print(f"{path.name}: {len(page_rows)} reviews")

    unique_rows = []
    seen = set()
    for row in rows:
        key = (row["reviewer"], row["date"], row["review"])
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)

    fields = [
        "page",
        "offset",
        "reviewer",
        "rating",
        "date",
        "review",
        "reviewer_url",
        "source_file",
    ]
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"Wrote {len(unique_rows)} unique reviews to {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
