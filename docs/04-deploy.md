# Deploying UFMS — the click path, and what is already proved

**The deployed URL is a bonus. The demonstration runs from localhost.** Both
free tiers involved go to sleep — Render's web service spins down after 15
minutes idle and takes about a minute to wake, and Aiven powers a free database
off after a period of inactivity. A cold start in front of an examiner is a
worse failure than having no URL at all. Follow `03-demo-runbook.md` on the day;
treat this as a line on a slide and a genuine test that the configuration is
portable.

Time-box the attempt to one working session. If a provider asks for a card,
stop and write down where it stopped.

---

## What has already been verified, locally, end to end

This is not a plan. The whole path below was executed on 10 September 2026
against a second, empty MySQL container standing in for the hosted database, and
it works:

| Step | Result |
|---|---|
| Fresh, empty MySQL 8.0 | — |
| `alembic upgrade head` | builds all 32 tables and the 3 views from nothing |
| Restore `data/processed/demo_data.sql` | 4,820 rows, 612 KB, idempotent on a second run |
| `pip install -r requirements-api.txt` into an empty venv | 335 MB, vs 473 MB for the full one |
| Boot with `ENVIRONMENT=production DEBUG=false` | starts; refuses to start on a placeholder secret |
| `scripts/check_parity.py` against the full local instance | **27/27 invariants, and all five endpoints byte-identical** |

So the risky part — "will a database holding only the derived tables serve the
same numbers?" — is answered. It does, to a relative tolerance of 1e-9, on
every field of every endpoint.

What is **not** verified is the part needing an account: Aiven's TLS
requirements against PyMySQL, and Render's build. Those are flagged below.

## Why the database is 612 KB and not 215 MB

The five endpoints read the derived tables and their lookups — nine tables,
4,820 rows. None of them touches `weather_observations` (1,309,896 rows,
146 MB) or `complaints` (237,157 rows, 64 MB): those are inputs to
`app/derived/`, which has already run. `scripts/export_demo_dump.py` dumps
exactly the closure the repositories reach, and re-checks the foreign keys on
every run so it cannot silently go stale.

This also keeps engineering rule 7 true by construction — nothing here is within
three orders of magnitude of a 1 GB tier.

`users` is deliberately excluded, so the shared local demo password cannot be
published through the dump. The deployed instance gets its own accounts.

---

## 1. The database — Aiven MySQL

Checked 10 September 2026: Aiven still offers an always-free managed MySQL,
1 GB storage and 1 GB RAM, single node, **no credit card**. It powers off after
a period of inactivity, with warning by email.

MySQL 8 on a free tier is genuinely scarce — most providers offer Postgres.
**Do not port the schema to Postgres to get a free tier.** That is a rewrite
days before a freeze, and the migrations, the canonical DDL and
`test_migrations.py` all assume MySQL.

1. Sign up at aiven.io, create a MySQL service on the free plan.
2. Copy the connection details. Aiven **requires TLS**, so the URL needs its CA:

   ```
   mysql+pymysql://USER:PASSWORD@HOST:PORT/defaultdb?ssl_ca=/etc/secrets/aiven-ca.pem
   ```

   Download their `ca.pem` and add it to Render as a **Secret File** named
   `aiven-ca.pem` — Render mounts secret files at `/etc/secrets/`.

   > **Untested.** Everything else here was run; this was not, because it needs
   > an account. If PyMySQL rejects the connection, the error to expect is
   > *"Connections using insecure transport are prohibited"*, which means the
   > `ssl_ca` parameter is not reaching the driver. Trying `ssl_verify_cert=true`
   > alongside it is the next thing to try. Budget half an hour for this step
   > specifically; it is the most likely place to lose time.

3. Build the schema and load the data from your laptop, pointing at Aiven:

   ```bash
   DATABASE_URL='mysql+pymysql://...' alembic upgrade head
   mysql --default-character-set=utf8mb4 -h HOST -P PORT -u USER -p DBNAME \
       < data/processed/demo_data.sql
   ```

   The charset flag is not optional — without it two column comments are stored
   double-encoded.

4. Create accounts. **Do not copy the local ones**, whose password is shared and
   obvious:

   ```bash
   DATABASE_URL='mysql+pymysql://...' python scripts/create_user.py \
       --email officer@ufms-demo.org --name "Demo Officer" --role officer
   DATABASE_URL='mysql+pymysql://...' python scripts/create_user.py \
       --email admin@ufms-demo.org --name "Demo Admin" --role admin
   ```

   Each prints a generated password once. Record them. Note that
   `email-validator` rejects reserved TLDs, so `…@something.test` will fail at
   login with a 422 — use a real-looking domain.

## 2. The API — Render

Free web service, no card. Spins down after 15 minutes idle; ~1 minute to wake.
750 instance-hours a month.

1. New → Blueprint, point it at the repository. It reads `render.yaml`.
2. It will prompt for the two values marked `sync: false`:
   - `DATABASE_URL` — the Aiven string from above.
   - `CORS_ORIGINS` — a **JSON array**, e.g. `["https://ufms-demo.vercel.app"]`.
     Not a bare string. Leave this until the frontend URL exists, then set it.
3. `SECRET_KEY` is generated by Render. Do not set it by hand.

`app/core/config.py` refuses to boot in production with the placeholder secret,
with anything under 32 characters, or with `DEBUG=true`. A misconfigured deploy
therefore fails immediately with a readable message instead of quietly serving
forgeable tokens.

## 3. The frontend — Vercel

1. Import the repository. **Set the root directory to `frontend/`.**
2. Edit `frontend/vercel.json` and replace `REPLACE-ME.onrender.com` with the
   Render hostname, then commit.

   The rewrite is the reason there is no CORS to get wrong: the browser only
   ever talks to the Vercel origin, and Vercel forwards `/api/*` to Render. This
   is the same arrangement the Vite dev proxy gives locally, which is why the
   deployed and local setups do not differ.

   The alternative is `VITE_API_BASE_URL=https://…onrender.com` as a build
   environment variable, which makes the browser call Render directly. That
   works, but then `CORS_ORIGINS` on the API has to name the Vercel origin
   exactly — protocol, host, no trailing slash — and a mismatch shows up as
   every screen rendering empty against an API that is working perfectly.

3. Redeploy after changing either.

## 4. Prove it, before believing it

```bash
python scripts/check_parity.py \
    --base http://127.0.0.1:8000 \
    --other https://ufms-api.onrender.com \
    --other-email officer@ufms-demo.org --other-password 'the-generated-one'
```

This asserts the 27 frozen figures against both instances — precision@20
14.0809% with its 4.79% floor and 37.72% ceiling, the frozen top-20 in rank
order, Jakkur's series, ρ = +0.474 against ρ = +0.082 — and then diffs every
field of all five payloads.

**If it disagrees on anything, the instance is not deployed, it is broken, and
it must not be shown.** The usual causes, in order: the `derive` step never ran
on the source database before the dump; the restore hit a constraint and stopped
half way; the API is pointed at the wrong database.

Allow the first request a minute — that is a cold start, not a failure. The
script's timeout is 120 seconds for exactly this reason.

## If you have to stop

Write down where it stopped and move on. Deployment is worth a mark or two out
of twenty; the paper is thirty. The system demonstrates from localhost either
way, and `03-demo-runbook.md` is what actually gets followed on the day.
