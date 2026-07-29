# Medication Request Service

A FastAPI service for recording medications prescribed to patients by clinicians. Patients,
clinicians and medications are treated as reference data that already exists and gets loaded by a
seed script. This service owns the medication requests that link them.

The business rules live in [`app/domain/rules.py`](app/domain/rules.py) as plain functions with no
framework imports, which is the quickest way to see what the service actually enforces.

## Setup

### Docker (PostgreSQL)

```bash
docker compose up --build
```

Applies the migrations and loads the reference data before serving. Docs at
<http://localhost:8000/docs>.

The database is published on host port 5433.

### Local (SQLite, nothing else needed)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

`DATABASE_URL` defaults to a local SQLite file. Copy `.env.example` to `.env` to point it at
PostgreSQL instead. The app, the migrations and the tests all read that one setting.

### Try it

Seed IDs are fixed, so this works as written:

```bash
PATIENT=11111111-1111-4111-8111-111111111111

curl -X POST "http://localhost:8000/patients/$PATIENT/medication-requests" \
  -H 'Content-Type: application/json' \
  -d '{
        "clinician_id":    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "medication_id":   "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "prescribed_date": "2026-03-01",
        "start_date":      "2026-03-02",
        "end_date":        "2026-03-16",
        "frequency":       "3 times/day"
      }'

curl "http://localhost:8000/patients/$PATIENT/medication-requests?status=active"
```

Run the create twice and the second returns 409, because the dates overlap.

## Testing

```bash
pytest                                      # 143 tests
pytest --cov=app --cov-report=term-missing  # 94% line coverage
ruff check . && ruff format --check . && mypy
```

The suite builds a throwaway SQLite database using the real migrations, so each run also proves the
migrations apply. Every test runs in a transaction that gets rolled back, which keeps tests isolated
while still letting the service layer commit exactly as it does in production.

To run against PostgreSQL, with the Docker stack up:

```bash
docker compose exec db createdb -U medication medication_requests_test
DATABASE_URL=postgresql+psycopg://medication:medication@localhost:5433/medication_requests_test pytest
```

All 143 pass on both backends.

## Assumptions

The brief leaves some things open. These are the calls I made, and each one is reversible.

- **A missing end date means open ended**, so for the overlap rule it counts as running indefinitely.
  One open ended active request therefore blocks any later request for the same medication, and
  recording a new one means closing off the old one with an end date first. Reading it the other way,
  as "end date not recorded yet", would make the overlap rule trivial to bypass by leaving the field
  blank.
- **Effective periods include both ends**, so two requests sharing a single day overlap.
- **Only active requests take part in the overlap rule**, following the wording "more than one Active
  medication request". Cancelled and completed requests block nothing.
- **Returning to active is the only forbidden status change.** Everything else is allowed, including
  completed to cancelled.
- **PATCH rejects fields outside the permitted set** rather than ignoring them. The brief allows
  either. Ignoring them means a client gets a 200 for a change that did not happen.
- **The patient comes from the URL.** A `patient_id` in the request body is rejected, so there is
  never a question of which one wins.
- **New requests default to active.**
- **Registration IDs are unique**, enforced with a database constraint. **Medication codes are not**,
  because the brief models strength and form separately from the code, which suggests one code covers
  several variants.
- **Prescribed date is not checked against start date.** Backdated prescriptions are real and the
  brief does not say, so adding that rule would be inventing one.
- **Frequency is free text**, and there is no authentication.

## Future improvements

1. **Close the overlap race.** The rule reads, decides, then writes, so two simultaneous requests can
   both pass the check and create the overlap it exists to prevent. PostgreSQL can enforce it properly
   with a `btree_gist` exclusion constraint on patient, medication and date range where status is
   active. I verified that constraint works against the compose database. It would make the overlap
   impossible regardless of how the data arrives.
2. **Authentication, authorisation and an audit trail.** This is identifiable patient data.
3. **CI** running ruff, mypy and pytest against both SQLite and a real PostgreSQL container, plus
   `alembic check` to catch model and migration drift.
4. **Optimistic concurrency on PATCH** using `ETag` and `If-Match`, so two people editing the same
   request cannot silently overwrite each other.
5. **Cursor based pagination.** Offset paging is fine at this size but can skip or repeat rows as data
   changes between pages.
6. **Status history**, so the full prescribing timeline is recoverable rather than only the current
   state. Left out because it expands the domain model past what the brief describes.
7. **Map database constraint violations to 409** instead of letting them surface as a 500.

## AI assisted development

I used Claude Code throughout, as a fast pair programmer. It generated a good deal of the code,
particularly the repetitive layers: models, schemas, the Alembic migration, and the Docker setup. It
was also useful for expanding test outlines into full parametrised suites, including boundary cases
around the overlap check I would probably not have written by hand.

I set the architecture and reviewed everything. The decisions that shaped the result were mine: pure
domain rules with no framework imports, the service layer owning transactions, one place that maps
errors to status codes, and working test first so the endpoint contracts existed as failing tests
before any implementation.

It needed correcting in a few places, mostly comments asserting things the brief never said, and one
case where an unstated assumption had quietly become a database constraint. I also had it prove two
claims about SQLite behaviour before relying on them.

Verified before submitting: 143 tests passing on SQLite and PostgreSQL, `mypy --strict` clean with no
ignores, ruff clean, and the Docker stack exercised by hand against real PostgreSQL.
