# Data Engineering Interview Rubrics

These original evaluation rubrics are a starter knowledge base for data-engineering
interviews, initially aimed at candidates with approximately 2–4 years of experience.
They are coaching criteria, not a claim that every employer uses the same standards.
Award credit only for evidence actually present in the candidate's answer.

## ETL and pipeline design

Look for a clear description of data sources, extraction approach, transformations,
destination, and how the pipeline is scheduled or triggered. Strong answers explain
why the design fits the volume, latency, and reliability requirements rather than
merely listing tools. Credit incremental processing, idempotency, retries, backfills,
and handling schema changes when the candidate gives concrete examples. Ask how the
candidate would detect and recover from a partial or failed load. Do not assume a
project used a particular cloud, orchestration framework, or distributed engine unless
the answer says so.

## SQL and query performance

Look for correct use of joins, filtering, aggregation, and window functions where
relevant to the problem. Strong answers explain how they investigated a slow query,
such as examining an execution plan, reducing scanned data, choosing appropriate
indexes or partition filters, and measuring the result. Distinguish a stated
optimization from a measured improvement. Give credit when the candidate describes
the SQL work and its purpose, even if they do not use the phrase "query optimization."

## Python and data processing

Look for maintainable Python used to ingest, validate, transform, or automate data
workflows. Strong answers describe input and output contracts, error handling,
logging, tests, and how the code handles larger-than-memory data. Pandas is suitable
for many in-memory workloads; distributed processing such as PySpark should be
justified by scale or operational constraints rather than treated as automatically
better. Do not infer Python proficiency from a project outcome unless the candidate
connects their contribution to Python.

## Data modeling and schema design

Look for how entities, keys, relationships, grain, and data types were selected.
Strong answers discuss trade-offs such as normalized versus analytics-oriented
structures, schema evolution, nullability, and backward compatibility. Credit
decisions grounded in actual consumers or query patterns. A list of tables alone is
not enough to show thoughtful modeling; ask what assumptions and constraints shaped
the schema.

## Cloud data platforms

Treat AWS, Google Cloud Platform (GCP), and Microsoft Azure as alternative cloud
platforms unless a role explicitly requires more than one. Credit a platform only
when the candidate names it and describes relevant work, such as storage, compute,
permissions, deployment, monitoring, or cost control. Do not infer cloud experience
from using an API, a database, or a local container. When a candidate has no cloud
experience, assess transferable design knowledge separately from hands-on experience.

## Data quality and validation

Look for checks that data is complete, accurate, timely, and consistent with expected
contracts. Strong answers identify what is checked, where checks run, what happens
when a check fails, and how bad data is quarantined or corrected. Examples include
schema and null checks, uniqueness constraints, reconciliation against source totals,
freshness monitoring, and representative test fixtures. Give extra weight to
measurable evidence such as fewer downstream defects or faster detection, when stated.

## Reliability, monitoring, and operations

Look for monitoring of pipeline success, latency, freshness, volume, and resource use.
Strong answers describe actionable alerts, ownership, runbooks, retry boundaries,
safe re-runs, and recovery or backfill procedures. Ask what the candidate personally
implemented and how they know it worked. A successful one-time migration is different
from an operated production pipeline; do not conflate the two.

## Communication and measurable impact

Look for clear ownership, collaboration with analysts or data scientists, and an
explanation of how the dataset met consumer needs. Strong answers use a concise
problem-action-result narrative and provide a credible outcome, such as reduced
runtime, improved freshness, lower query cost, fewer data defects, or less manual
work. Do not invent or extrapolate metrics. If no metric is available, encourage the
candidate to explain how they validated usefulness and what they would measure next.
