# n8n Job Board Tracker — Claude Skill

A Claude skill that walks you, step by step, through building your own n8n automation: check a list of companies' job boards (Greenhouse, Lever, or Ashby) and log any matching openings into a Google Sheet. No coding experience required — just an n8n Cloud account (free trial) and a Google account.

Built by [Nate Smith](https://www.linkedin.com/in/natedansmith/) — video walkthrough coming soon.

## What you need before you start

- A free [n8n Cloud](https://n8n.io) trial account
- A Google account (for the destination Sheet)
- Claude, on one of the three surfaces below

## Install the skill

Download `n8n-job-board-tracker.skill` from this repo's [Releases](../../releases) page, then install it on whichever Claude surface you use:

**Claude.ai (Pro, Max, or Free plan)**
1. Go to **Settings → Capabilities** and turn on **Code Execution** and **File Creation**.
2. Go to **Customize → Skills**, click **+**, then **+ Create skill**, and upload the `.skill` file.
3. Toggle the skill on.

**Claude Code**
Unzip it into your personal skills folder so it's available in every project:
```
unzip n8n-job-board-tracker.skill -d ~/.claude/skills/
```
Start a new Claude Code session and it'll pick up the skill automatically.

**Cowork**
Open the `.skill` file directly — you'll see a **Save skill** button that installs it into your profile.

## How to use it

Start a conversation and say something like:

> "I want to track job openings at Stripe, Ramp, and Highspot — help me build a tracker."

Claude will walk you through it one step at a time: confirming each company's job board, generating the exact code to paste into n8n, and getting everything flowing into a Google Sheet — including how to dedupe repeat postings and (optionally) run it automatically on a schedule.

## What's in this repo

- `SKILL.md` — the instructions Claude follows
- `scripts/` — helper scripts that generate the job-board URLs and the n8n code
- `references/` — the exact code for the trickier n8n node (handling three different job-board data formats)
