
import argparse
import csv
from pubmed_pharma_papers.pubmed_fetcher import fetch_pubmed_data

def main():
    parser = argparse.ArgumentParser(
        description="Fetch PubMed papers with pharma/biotech affiliations."
    )

    parser.add_argument("query", help="PubMed query string")
    parser.add_argument("-f", "--file", help="Output CSV filename")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--year", nargs="*", help="Filter by publication year(s)")

    args = parser.parse_args()

    papers = fetch_pubmed_data(
        query=args.query,
        limit=50, # Using a default limit, could be added as an argument later
        year_filter=args.year,
        debug=args.debug
    )

    if not papers:
        print("❌ No matching papers found with non-academic affiliations.")
        return

    if args.file:
        try:
            with open(args.file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=papers[0].keys())
                writer.writeheader()
                writer.writerows(papers)
            print(f"✅ Results saved to {args.file}")
        except IOError as e:
            print(f"❌ Error saving results to file: {e}")
    else:
        print(f"✅ {len(papers)} papers fetched with non-academic affiliations:")
        for i, paper in enumerate(papers, start=1):
            print(f"🔹 Paper {i}")
            for key, value in paper.items():
                print(f"{key}: {value}")
            print("-" * 40)

if __name__ == "__main__":
    main()
