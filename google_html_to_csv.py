import argparse
import csv
from pathlib import Path

from bs4 import BeautifulSoup


def node_text(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def parse_reviews(path: Path) -> list[dict[str, str | int]]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    rows = []

    for card in soup.select("div.bwb7ce"):
        review_id = card.get("data-id", "")
        reviewer = card.select_one(".rhtdWc")
        profile = card.select_one("a.yC3ZMb[href]")
        date = card.select_one(".m6Mr5d") or card.select_one(".y3Ibjb")
        review = card.select_one(".OA1nbd")
        rating_box = card.select_one(".h3PQJ")

        # Google renders five SVGs for every rating; filled stars have yellow paths.
        rating = (
            sum(
                path.get("fill", "").lower() == "#fabb05"
                for path in rating_box.select("svg path")
            )
            if rating_box
            else ""
        )

        # Remove the interactive "More" label from saved, expanded or truncated text.
        if review:
            for more_link in review.select('a[aria-label^="Read more"]'):
                more_link.decompose()

        rows.append(
            {
                "review_id": review_id,
                "reviewer": node_text(reviewer),
                "rating": rating,
                "date": node_text(date),
                "review": node_text(review),
                "reviewer_url": profile.get("href", "") if profile else "",
                "source_file": path.name,
            }
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert saved Google review HTML to CSV")
    parser.add_argument(
        "input",
        nargs="?",
        default="review_pages/alo_review_google/alo mtl reviews - Google Search example.html",
        help="Saved Google review HTML file",
    )
    parser.add_argument(
        "--output",
        default="alo_google_reviews.csv",
        help="Destination CSV file",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")

    rows = parse_reviews(input_path)

    # data-id is Google's stable identifier within this saved result set.
    unique_rows = []
    seen = set()
    for row in rows:
        key = row["review_id"] or (
            row["reviewer"],
            row["date"],
            row["review"],
        )
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)

    fields = [
        "review_id",
        "reviewer",
        "rating",
        "date",
        "review",
        "reviewer_url",
        "source_file",
    ]
    output_path = Path(args.output)
    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"Wrote {len(unique_rows)} unique reviews to {output_path.resolve()}")


if __name__ == "__main__":
    main()
