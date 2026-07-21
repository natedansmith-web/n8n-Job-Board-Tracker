#!/usr/bin/env python3
"""
Turn a confirmed list of {company, ats, feed_url} mappings into the exact
JavaScript array to paste into n8n's "Registry" Code node.

Usage:
    python build_registry_code.py confirmed.json

Where confirmed.json looks like:
    [
      {"company": "Stripe", "ats": "greenhouse", "feed_url": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"},
      {"company": "Ramp", "ats": "ashby", "feed_url": "https://api.ashbyhq.com/posting-api/job-board/ramp"}
    ]

Prints ready-to-paste JavaScript to stdout.
"""
import argparse
import json


def build_js(registry):
    lines = ["const registry = ["]
    for i, r in enumerate(registry):
        comma = "," if i < len(registry) - 1 else ""
        lines.append(
            f'  {{"company": {json.dumps(r["company"])}, "ats": {json.dumps(r["ats"])}, '
            f'"feed_url": {json.dumps(r["feed_url"])}}}{comma}'
        )
    lines.append("];")
    lines.append("return registry.map(r => ({ json: r }));")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("confirmed_json", help="Path to JSON file of confirmed {company, ats, feed_url} entries")
    args = parser.parse_args()

    with open(args.confirmed_json) as f:
        registry = json.load(f)

    print(build_js(registry))


if __name__ == "__main__":
    main()
