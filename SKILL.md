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
- URL field, switch to **Expression** mode, enter:
  ```
  {{ $json.feed_url + ($json.feed_url.includes('?') ? '&' : '?') + 't=' + Date.now() }}
  ```
  The extra `t=` timestamp isn't decoration — job-board APIs sit behind caches (CDNs) that can quietly serve responses that are *days or weeks* old, meaning brand-new postings never show up even though the feed "works." Adding a unique timestamp to every request forces a fresh response every time. All four platforms ignore the unknown parameter, so it's harmless — and it prevents the single hardest-to-diagnose failure this workflow has (a real posting on the company's site that never appears in your Sheet, with no error anywhere).
- Settings → **On Error: Continue** (one dead feed shouldn't kill the whole run)
- If tracking more than ~15 companies, Options → add **Batching**: 10 items per batch, 200ms interval (polite to the APIs)

Execute it — they should see a raw JSON response per company.

## Step 5 — Normalize node

Greenhouse, Lever, Ashby, and Workable all return job data in different shapes. This step translates all four into one consistent format so nothing downstream needs to care which platform a company uses. The exact code is in `references/node-code.md` — paste it into a new Code node named exactly `Normalize`, execute, and confirm every company's jobs now show the same fields: company, job_id, title, location, url, posted.

## Step 6 — Filter step

Ask two questions before building anything:

1. **What job titles or keywords matter?** (e.g. "Customer Success," "Product Manager," "Senior or Staff Engineer")
2. **Any location constraints?** (remote-only, specific regions, countries to exclude) — ask this explicitly rather than skipping it; the Normalize step outputs a clean `location` field for exactly this purpose. But how you *implement* the answer matters a lot — see below.

**Choosing the tool — Filter node vs. Code node:**
- If the title need is a simple keyword list ("any title containing X, Y, or Z"), a **Filter node** with OR'd contains-conditions works fine.
- If the need is compound — e.g. "senior **or** staff, **and** engineer" — use a **Code node** instead. The Filter node combines all its conditions with a single AND/OR across the whole list (no per-group logic), so a compound requirement either over-matches ("Senior Product Manager" sneaks in) or under-matches. Don't fight the UI; a few lines of code express it cleanly:

```javascript
// Every pattern in TITLE_MUST has to match the title.
// Put OR-groups inside one regex, AND-groups as separate array entries.
const TITLE_MUST = [/senior|staff/i, /engineer/i];
// Optional location handling — EXCLUSION ONLY, tested against title+location
// combined. Leave as null to skip location filtering entirely (recommended).
const LOCATION_BLOCK = null; // e.g. /london|emea|apac/i

return $input.all().filter(item => {
  const title = item.json.title || '';
  const hay = title + ' ' + (item.json.location || '');
  return TITLE_MUST.every(re => re.test(title)) &&
         (!LOCATION_BLOCK || !LOCATION_BLOCK.test(hay));
});
```

**Location rules, whichever tool they use:**
- **Default recommendation: no location filter at all** — a false positive costs two seconds deleting a row from the Sheet; a false negative is a job they never knew existed. That asymmetry should drive the design.
- If they do want one, make it a **single "does not match" exclusion** of obviously-wrong regions — never a required inclusion. Location strings are wildly inconsistent across companies ("Remote," "United States," "Austin, TX," "US Central," or blank can all describe the same remote-eligible role), and the region sometimes appears only in the *title*.
- Always test location patterns against **title and location combined** (the `hay` variable above), and never let a blank location auto-fail a row.

**Regex lessons from running this in production** — apply these when writing any pattern for the user:

- **Always use the `/i` flag** (case-insensitive). Job titles capitalize unpredictably.
- **Use word boundaries on short tokens**: `\bcsm\b` not `csm` (which matches inside other words), `\bus\b` not `us` (which matches "status," "campus"). Long phrases like "customer success" don't need them.
- **Never AND multiple *inclusion* patterns on the same messy field.** Requiring location to match both "remote-ish" AND "US-ish" silently dropped real roles located "Austin, TX" (no country word), "United States" (no "remote" word — how remote-first companies list everything), and "US Central" (region only in the title). Each ANDed inclusion multiplies the silent-loss rate. One inclusion max per field; everything else should be exclusions.
- **Add a title *exclusion* for adjacent roles.** A broad net like "customer success" also catches "Senior Recruiter, Customer Success" or "CS Enablement Manager" — roles *near* the function, not *in* it. Pair the inclusion with an exclusion like `/recruit|sourc|enablement|\bengineer|intern\b/i` tuned to the user's field.
- **Account for variant separators and spellings** the user cares about: `tech[- ]touch` catches both "tech-touch" and "tech touch"; `programs?` catches singular and plural.
- **Test the pattern against real strings before trusting it.** Take 2–3 titles from an actual feed response that *should* match and 1–2 that shouldn't, and check them against the pattern by eye. Every silent failure today would have been caught by this 60-second habit.

Execute and confirm the list shrinks to just relevant roles — then have the user spot-check one role they *know* should match, by hand, before moving on.

## Step 7 — Google Sheets node (with built-in dedup)

This workflow is meant to be re-run — by hand or on a schedule — so it needs to not re-log the same job twice. The cleanest way is to let the Sheet itself handle that, using the Sheets node's **Append or Update Row** operation keyed on `job_id`: a job already in the Sheet gets its row updated in place, a new job gets appended. Every run is *idempotent* — the user can re-run freely while troubleshooting and the Sheet just converges to the current truth, with no hidden state anywhere. (Deliberately avoid n8n's Remove Duplicates "previous executions" node here — it keeps an invisible history database that swallows items during test runs and turns every troubleshooting loop into a clear-the-history ritual. Bad fit for a first build.)

Guide them through:
1. Create a new Google Sheet with a header row: `Company | Title | Location | URL | Posted | Job ID`
2. In n8n, add a **Google Sheets** node after Filter, connect their Google account (OAuth2 — n8n walks through this in-app), pick the sheet, and set operation to **Append or Update Row**.
3. Set the **Column to Match On** to `Job ID`. (If the column doesn't appear in the dropdown, the node cached an old header — click the refresh icon by the column list or re-select the sheet name.)
4. **Map each column using expressions** — this is the step people miss. Once the sheet is selected, n8n shows a **Values to Send** section with one input box per column from the header row. Each box needs the matching field as an expression, not typed-out text: hover over the box, switch it to **Expression** mode (the toggle that appears, or click the gears/fx icon), and enter:
   - Company → `{{ $json.company }}`
   - Title → `{{ $json.title }}`
   - Location → `{{ $json.location }}`
   - URL → `{{ $json.url }}`
   - Posted → `{{ $json.posted }}`
   - Job ID → `{{ $json.job_id }}`
   If they leave a box in plain-text mode and type `$json.company`, the Sheet will literally fill with the text "$json.company" instead of real values — tell them to check for the green `{{ }}` expression styling in each box. (Drag-and-drop from the input panel on the left onto each box does the same thing and is often easier.)
5. Execute the whole workflow end to end and confirm real rows land in the Sheet — real company names and titles in the cells, not literal `$json...` text. Before running, do a last visual pass over the **Values to Send** boxes: every one of the six should show the green `{{ }}` expression styling. Any box showing plain black text is still in fixed mode and will write its literal contents into every row.
6. **Prove the idempotency:** run the whole workflow a second time immediately. The Sheet should be unchanged — same rows, nothing doubled. That's the design working; tell the user this is why they can re-run fearlessly from now on.

One trade-off to mention honestly: the Sheet is a living mirror of every currently-matching job, not an inbox of only-new items. "What's new since yesterday" = sort by the Posted column. For a first build, that's a much better deal than hidden dedup state.

## Step 8 — Automate it (optional but worth offering)

Right now the workflow only runs when someone clicks "Execute Workflow." Ask if they'd like it to check automatically instead. If so:
- Add a **Schedule Trigger** node (alongside or in place of the Manual Trigger — n8n workflows can have more than one trigger) and set it to run once a day at whatever time they want (e.g., 7am).
- Because this is running on n8n Cloud rather than a personal computer, the schedule fires reliably even if their laptop is closed or asleep — worth calling out explicitly, since that's a real limitation people hit with self-hosted n8n.
- Combined with the Append-or-Update design, this turns the workflow into a genuine check-while-you-sleep system: they open the Sheet each morning, sort by Posted, and see what's new — no repeats, ever.

This is optional — the workflow is fully useful run manually — so don't push it if they'd rather stay hands-on.

## Wrap up

They now have a live tracker covering their target companies with no repeat entries, optionally running on its own schedule. Mention they can add more companies later by re-running Step 2 for just the new ones and appending them to the Registry code.

## Troubleshooting

- **Zero rows land in the Sheet and the Filter output was also empty** → the Filter keywords are probably too narrow; loosen them and re-run.
- **Sheets node errors with "columns.matchingColumns is required"** → the **Column to Match On** field is empty; set it to `Job ID`. If `Job ID` isn't offered in the dropdown, the node cached the old header — refresh the column list or re-select the sheet so it re-reads the header row.
- **Every run doubles the rows in the Sheet** → the node is on plain **Append Row** instead of **Append or Update Row**, or the match column isn't set to `Job ID`. Fix either and re-run — the duplicates from before will need a one-time manual cleanup in the Sheet.
- **HTTP Request errors on one company** → that company's platform/slug mapping is likely wrong; redo Step 2 for just that one.
- **Google Sheets node auth fails** → the OAuth credential needs reconnecting inside n8n.
- **A company doesn't map to any of the four platforms** → it's probably on Workday or a custom system this workflow doesn't cover; skip it rather than guessing a wrong slug.
- **The company's careers page shows a job that never appears in the Sheet** → three known causes, in order of likelihood: (1) *Stale cache* — the feed served an old cached copy; confirm the HTTP Request URL includes the `t=' + Date.now()` cache-buster from Step 4, then re-run. (2) *Over-strict filter* — take the exact title from the careers page and check it against the Filter keywords by hand; loosen if it doesn't match. (3) *Ashby under-reporting* — Ashby's public posting API sometimes omits roles that are live on the company's board (a known limitation of that endpoint, not a bug in the workflow). If an Ashby company is important to the user, suggest they spot-check its board page directly now and then; supporting Ashby's richer board endpoint is a possible future upgrade, not part of this walkthrough.
