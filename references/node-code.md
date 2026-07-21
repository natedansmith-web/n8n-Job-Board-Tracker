# Normalize node — exact code

Greenhouse and Ashby both wrap jobs in a `{"jobs": [...]}` array but use different field names inside each job object. Lever returns a plain array where each item IS one job. This code handles all three shapes and outputs one consistent record per job: `company`, `job_id`, `title`, `location`, `url`, `posted`.

Paste this into a Code node renamed exactly `Normalize`, placed right after the HTTP Request node:

```javascript
const out = [];
const items = $input.all();
for (let i = 0; i < items.length; i++) {
  const reg = $('Registry').itemMatching(i).json;
  const d = items[i].json || {};
  if (d.error) continue;

  if (Array.isArray(d.jobs)) {
    // Greenhouse and Ashby both wrap jobs in an array, but the job objects differ
    for (const job of d.jobs) {
      if (reg.ats === 'greenhouse') {
        out.push({ json: {
          company: reg.company,
          job_id: reg.company + '-' + job.id,
          title: job.title,
          location: (job.location && job.location.name) || '',
          url: job.absolute_url,
          posted: job.first_published
        }});
      } else { // ashby
        const secondaries = (job.secondaryLocations || []).map(l => (l && l.location) || l).filter(Boolean);
        const loc = [job.location, ...secondaries].filter(Boolean).join('; ') + (job.isRemote ? '; Remote' : '');
        out.push({ json: {
          company: reg.company,
          job_id: reg.company + '-' + (job.id || job.jobUrl || job.title),
          title: job.title,
          location: loc,
          url: job.jobUrl || job.applyUrl || '',
          posted: job.publishedAt || ''
        }});
      }
    }
  } else if (d.id && d.text) {
    // Lever feeds return arrays, so each item IS one job
    out.push({ json: {
      company: reg.company,
      job_id: reg.company + '-' + d.id,
      title: d.text,
      location: (d.categories && d.categories.location) || '',
      url: d.hostedUrl || '',
      posted: d.createdAt || ''
    }});
  }
}
return out;
```

## Filter node guidance

Ask the user what titles/keywords matter to them, then build a Filter node with a condition on `{{ $json.title }}` — operation "contains" (case-insensitive), one condition per keyword joined with OR. Example for someone targeting Customer Success roles: keywords might be `customer success`, `csm`, `account manager`. If n8n's Filter node UI only supports AND between conditions in their version, use a Code node instead with a simple regex test, e.g.:

```javascript
const keywords = /customer success|csm|account manager/i;
return $input.all().filter(item => keywords.test(item.json.title));
```

## Google Sheets column mapping

Header row: `Company | Title | Location | URL | Posted`
Map from Normalize's output fields: `company → Company`, `title → Title`, `location → Location`, `url → URL`, `posted → Posted`.
