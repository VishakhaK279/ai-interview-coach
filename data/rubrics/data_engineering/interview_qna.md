# Data Engineering Interview Q&A

## Question 1
Explain Medallion Architecture in GCP.
**Answer:**  
Bronze = raw ingestion, Silver = cleaned/validated, Gold = business-ready aggregates. Ensures progressive data quality and usability.

---

## Question 2
How do you handle Spark data skew?
**Answer:**  
Use salting keys, repartitioning, map-side combine, and monitor skew metrics in Spark UI.

---

## Question 3
What does “exactly-once” mean in streaming pipelines?
**Answer:**  
Each event is processed once and only once, even with retries or failures. Achieved via idempotent writes and checkpointing.

---

## Question 4
How do you design retries and backfills in Airflow?
**Answer:**  
Configure `retry_delay`, `max_retries`, and use backfill DAG runs. Ensure tasks are idempotent to avoid duplicate processing.

---

## Question 5
How do you implement CI/CD for GCP data pipelines?
**Answer:**  
Use Cloud Build + GitHub Actions for deployment, unit tests for SQL/Python, and automated schema validation before release.

---

## Question 6
How do you reconcile dashboards vs ERP data?
**Answer:**  
Build reconciliation scripts comparing aggregates, row counts, and key metrics. Automate alerts for mismatches.

---

## Question 7
How do you integrate SAP or CRM data into GCP?
**Answer:**  
Use Cloud Data Fusion connectors or APIs, ingest into Bronze layer, validate schema, then transform into Silver/Gold.

---

## Question 8
What are DataOps best practices in GCP?
**Answer:**  
Automated testing, CI/CD pipelines, monitoring with Cloud Logging, and enforcing coding standards for SQL/Python.

---

## Question 9
How do you ensure minimal disruption during BigQuery migration?
**Answer:**  
Use dual-write strategy, reconciliation scripts, and cut-over during low-traffic hours. Validate schema and row counts before switching.

---

## Question 10
How do you implement data lineage and governance in GCP?
**Answer:**  
Use Data Catalog for metadata, Cloud Composer for orchestration lineage, and enforce IAM + audit logs for governance.

---

## Question 11
Explain OLTP vs OLAP.
**Answer:**  
OLTP handles transactional workloads with frequent inserts/updates. OLAP supports analytical queries with large aggregations.

---

## Question 12
What is Slowly Changing Dimension (SCD Type 2)?
**Answer:**  
Tracks historical changes by adding new rows with versioning and effective dates, preserving full history.

---

## Question 13
How do you optimize ETL pipelines in Spark?
**Answer:**  
Use partitioning, caching, broadcast joins, and avoid shuffles. Monitor with Spark UI for bottlenecks.

---

## Question 14
How do you manage schema evolution in BigQuery?
**Answer:**  
Use schema migration scripts, version control, and backward-compatible changes. Communicate updates to downstream teams.

---

## Question 15
How do you design a data lakehouse?
**Answer:**  
Combine raw data storage with structured query layers. Use Medallion architecture for progressive refinement.

---

## Question 16
How do you implement data quality checks?
**Answer:**  
Define rules for nulls, duplicates, ranges. Automate checks with Great Expectations or custom SQL assertions.

---

## Question 17
How do you handle late-arriving data in streaming?
**Answer:**  
Use watermarking, windowing, and deduplication strategies. Configure event-time vs processing-time appropriately.

---

## Question 18
How do you secure data in GCP?
**Answer:**  
Use IAM roles, VPC Service Controls, encryption at rest and in transit, and audit logging.

---

## Question 19
How do you monitor data pipelines?
**Answer:**  
Use Cloud Monitoring, custom metrics, and alerting. Track latency, throughput, and error rates.

---

## Question 20
How do you estimate effort for a data migration project?
**Answer:**  
Break tasks into phases (schema mapping, pipeline migration, validation). Use story points, past benchmarks, and resource allocation planning.
