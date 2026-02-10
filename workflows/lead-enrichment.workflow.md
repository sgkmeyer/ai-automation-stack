# Lead Research + Enrichment MVP (n8n)

## Inputs
- CSV upload (default)
- Columns expected: `company`, `domain`, `contact_name` (optional), `source` (optional)

## Nodes (Suggested)
1. **Manual Trigger** or **Cron**
2. **Read Binary File** (CSV upload)
3. **Spreadsheet File** → JSON
4. **Function**: normalize domain + company name
5. **HTTP Request**: company lookup (placeholder for chosen API)
6. **HTTP Request**: email discovery (placeholder for chosen API)
7. **HTTP Request**: Openclaw enrichment
   - URL: `https://openclaw.satoic.com/enrich`
   - Body: company + domain + role
8. **Function**: score lead
9. **Postgres**: upsert into `leads`
10. **Slack** or **Email**: summary report

## Postgres Upsert (example)
```sql
INSERT INTO leads (company, domain, contact_name, email, role, linkedin, source, enrichment_json, score)
VALUES ({{ $json.company }}, {{ $json.domain }}, {{ $json.contact_name }}, {{ $json.email }}, {{ $json.role }}, {{ $json.linkedin }}, {{ $json.source }}, {{ $json.enrichment_json }}, {{ $json.score }})
ON CONFLICT (domain, email)
DO UPDATE SET
  company = EXCLUDED.company,
  contact_name = EXCLUDED.contact_name,
  role = EXCLUDED.role,
  linkedin = EXCLUDED.linkedin,
  source = EXCLUDED.source,
  enrichment_json = EXCLUDED.enrichment_json,
  score = EXCLUDED.score,
  updated_at = NOW();
```

## Notes
- Replace API nodes with your provider of choice.
- Add a throttle node if you need to stay within API rate limits.
