#!/usr/bin/env python3
"""
Generate candidate ATS (Greenhouse/Lever/Ashby/Workable) feed URLs for a list of company names.

Usage:
    python generate_candidates.py "Stripe" "Figma" "Datadog" "Cockroach Labs"
    python generate_candidates.py --file companies.txt   # one company name per line

Output: JSON list of {company, ats, slug, url} candidates, two slug variants
(bare and hyphenated) times four platforms, per company. Feed this list of
URLs to a fetch step (or to the human, for manual browser checking) to find
out which candidates are actually live.
"""
import argparse
import json
import re
import sys


def slugs_for(name: str):
    """Return the distinct slug variants worth trying for a company name."""
    lowered = name.lower().strip()
    bare = re.sub(r"[^a-z0-9]", "", lowered)
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    variants = []
    for s in (bare, hyphenated):
        if s and s not in variants:
            variants.append(s)
    return variants


ATS_BUILDERS = {
    "greenhouse": lambda slug: f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": lambda slug: f"https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": lambda slug: f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "workable": lambda slug: f"https://apply.workable.com/api/v1/widget/accounts/{slug}",
}


def build_candidates(companies):
    out = []
    for company in companies:
        for slug in slugs_for(company):
            for ats, build_url in ATS_BUILDERS.items():
                out.append({
                    "company": company,
                    "ats": ats,
                    "slug": slug,
                    "url": build_url(slug),
                })
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("companies", nargs="*", help="Company names, space-separated (quote multi-word names)")
    parser.add_argument("--file", help="Path to a text file with one company name per line")
    args = parser.parse_args()

    companies = list(args.companies)
    if args.file:
        with open(args.file) as f:
            companies.extend(line.strip() for line in f if line.strip())

    if not companies:
        parser.error("Provide company names as arguments or via --file")

    print(json.dumps(build_candidates(companies), indent=2))


if __name__ == "__main__":
    main()
