---
name: n8n-job-board-tracker
description: Walks a user step by step through building their own n8n automation that checks a list of companies' job boards (Greenhouse, Lever, Ashby, or Workable) and logs any matching openings into a Google Sheet — no coding experience required. Trigger this skill whenever the user wants to build a job-search tracker or "job board bot," automate checking company career pages instead of doing it by hand, wants alerts/a spreadsheet of new postings from specific target companies, mentions building the workflow from Nate Smith's n8n walkthrough video/post, or asks anything like "how do I stop manually checking 15 job boards every morning."
---

# n8n Job Board Tracker Builder

This skill walks a real person — who may never have used n8n, written code, or called an API before — through building a working automation: check a list of companies' career pages, and drop any matching job openings into a Google Sheet. By the end they'll have a live n8n workflow they can re-run any time.

## Why the pacing matters

This is a guided walkthrough, not a document to dump on someone all at once. If you hand over all the steps in one message, a first-time builder loses track of which node they're stuck on and where to paste what. Complete one step, get a real confirmation signal back from the user (the node ran, it shows green, they pasted output, they said "done"), and only then move to the next step. If something didn't work, help them fix that step before moving on — don't plow ahead with a broken foundation.

Explain *why* each piece exists as you go, not just what to click. Someone who understands why the Normalize step exists will be able to debug it later; someone who just followed clicks won't.

## Step 0 — Get the company list

Ask which companies they want to track job openings at. This can be a handful or a few dozen — just a plain list of names is fine (e.g. "Stripe, Figma, Datadog, Ramp").

## Step 1 — Set up n8n Cloud

Tell them to go to n8n.io and start a free Cloud trial (no self-hosting, no terminal, no npm — that's a deliberate choice so this works for anyone). Once they're in, have them create a new, blank workflow.

## Step 2 — Map each company to its job-board platform

Most company career pages are a thin wrapper around one of four underlying systems: **Greenhouse**, **Lever**, **Ashby**, or **Workable** (Workable shows up more often outside the US, especially Europe). Each one exposes a public JSON feed of open roles at a predictable URL pattern based on a "slug" derived from the company name. The plan: generate a few candidate URLs per company, then find out which one is actually real.

1. Run `scripts/generate_candidates.py` with the company list (see the script's `--help` for exact usage) to produce candidate URLs — it tries a plain slug and a hyphenated slug against all four platforms.
2. **If you currently have the ability to fetch URLs in this conversation** (web browsing, bash with internet access, etc.), try each candidate yourself and tell the user which platform + slug worked for each company. A working feed returns real JSON — Greenhouse/Ashby/Workable return something like `{"jobs": [...]}`, Lever returns a plain `[...]` array of job objects. A dead one 404s or returns HTML.
3. **If you don't have fetch access, or it's unreliable in this environment, don't guess.** Hand the candidate list back to the user and ask them to open each link in a browser tab and report back which ones loaded real JSON vs. an error page. This is slower but works identically for every user regardless of what Claude surface they're on — reliability matters more than saving them a few clicks.
4. Some companies won't match any of the four (Workday is the most common case — it's what most large enterprises like Microsoft, Oracle, Adobe, and Salesforce run on, and it doesn't expose a comparable public per-company feed — plus genuinely custom ATSes) — that's fine, just drop them from the list and tell the user which ones didn't map and why.

## Step 3 — Build the Registry node

Once every company has a confirmed platform + working slug, run `scripts/build_registry_code.py` with that confirmed list to generate the JavaScript array.

Tell the user:
1. Add a **Manual Trigger** node.
2. Add a **Code** node after it, rename it exactly `Registry`, and paste in the generated code.
3. Click execute on just that node — they should see one item per company come back.

## Step 4 — HTTP Request node

Add an **HTTP Request** node after Registry.
- URL field, switch to **Expression** mode, enter `{{ $json.feed_url }}`
- Settings → **On Error: Continue** (one dead feed shouldn't kill the whole run)
- If tracking more than ~15 companies, Options → add **Batching**: 10 items per batch, 200ms interval (polite to the APIs)

Execute it — they should see a raw JSON response per company.

## Step 5 — Normalize node

Greenhouse, Lever, Ashby, and Workable all return job data in different shapes. This step translates all four into one consistent format so nothing downstream needs to care which platform a company uses. The exact code is in `references/node-code.md` — paste it into a new Code node named exactly `Normalize`, execute, and confirm every company's jobs now show the same fields: company, job_id, title, location, url, posted.

## Step 6 — Filter node

Ask what job titles or keywords actually matter to them (e.g. "Customer Success," "Product Manager," "Solutions Engineer"). Build a Filter node condition that keeps only rows whose title contains one of those keywords (case-insensitive). Execute and confirm the list shrinks to just relevant roles.

## Step 7 — Remove Duplicates node

This workflow is meant to be re-run — by hand or on a schedule — so without this step, every re-run would re-log every job that still matches the filter, even ones already added yesterday. This node remembers what's already been seen between runs and only lets genuinely new postings through.

Add a **Remove Duplicates** node after Filter (before Google Sheets):
- Operation: **Remove Items Processed in Previous Executions**
- Compare: Selected Fields → Fields to Compare: `job_id`

n8n tracks what it's seen between executions automatically with this operation — no separate database needed. Execute it now: on this first run, everything passes through since there's no history yet. Tell the user that's expected, not a bug — the dedup effect only shows up starting on the *second* run.

## Step 8 — Google Sheets node

Guide them through:
1. Create a new Google Sheet with a header row: `Company | Title | Location | URL | Posted`
2. In n8n, add a **Google Sheets** node after Remove Duplicates, connect their Google account (OAuth2 — n8n walks through this in-app), pick the sheet, operation **Append Row**, and map each column to the matching field from Normalize.
3. Execute the whole workflow end to end and confirm real rows land in the Sheet.

## Step 9 — Automate it (optional but worth offering)

Right now the workflow only runs when someone clicks "Execute Workflow." Ask if they'd like it to check automatically instead. If so:
- Add a **Schedule Trigger** node (alongside or in place of the Manual Trigger — n8n workflows can have more than one trigger) and set it to run once a day at whatever time they want (e.g., 7am).
- Because this is running on n8n Cloud rather than a personal computer, the schedule fires reliably even if their laptop is closed or asleep — worth calling out explicitly, since that's a real limitation people hit with self-hosted n8n.
- Combined with Remove Duplicates, this turns the workflow into a genuine check-while-you-sleep system: they open the Sheet each morning and see only what's new, with no repeats.

This is optional — the workflow is fully useful run manually — so don't push it if they'd rather stay hands-on.

## Wrap up

They now have a live tracker covering their target companies with no repeat entries, optionally running on its own schedule. Mention they can add more companies later by re-running Step 2 for just the new ones and appending them to the Registry code.

## Troubleshooting

- **Zero rows land in the Sheet** → the Filter keywords are probably too narrow; loosen them and re-run.
- **HTTP Request errors on one company** → that company's platform/slug mapping is likely wrong; redo Step 2 for just that one.
- **Every run re-adds jobs you've already seen** → double check the Remove Duplicates node is configured to compare on `job_id` and sits before the Google Sheets node, not after.
- **Google Sheets node auth fails** → the OAuth credential needs reconnecting inside n8n.
- **A company doesn't map to any of the four platforms** → it's probably on Workday or a custom system this workflow doesn't cover; skip it rather than guessing a wrong slug.
