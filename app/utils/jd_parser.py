"""Utilities for extracting a small set of known skills from job descriptions."""

import re

SKILL_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Python", ("python",)),
    ("Pandas", ("pandas",)),
    ("PySpark", ("pyspark",)),
    ("Apache Spark", ("apache spark", "spark")),
    ("Java", ("java",)),
    ("Scala", ("scala",)),
    ("JavaScript", ("javascript", "js")),
    ("TypeScript", ("typescript",)),
    ("SQL", ("sql",)),
    ("Hive", ("hive",)),
    ("Impala", ("impala",)),
    ("HBase", ("hbase",)),
    ("Alteryx", ("alteryx",)),
    ("Microsoft Fabric", ("microsoft fabric",)),
    ("HDFS", ("hdfs",)),
    ("MapReduce", ("mapreduce", "map reduce")),
    ("YARN", ("yarn",)),
    ("Kafka", ("kafka",)),
    ("NoSQL", ("nosql", "no sql")),
    ("Avro", ("avro",)),
    ("Parquet", ("parquet",)),
    ("CSV", ("csv",)),
    ("JSON", ("json",)),
    ("FastAPI", ("fastapi",)),
    ("Django", ("django",)),
    ("Flask", ("flask",)),
    ("React", ("react",)),
    ("Node.js", ("node.js", "nodejs")),
    (
        "Cloud Platforms",
        ("aws", "amazon web services", "gcp", "google cloud", "azure", "cloud"),
    ),
    ("Docker", ("docker",)),
    ("Containers", ("container technologies", "containerization", "containers")),
    ("Kubernetes", ("kubernetes",)),
    ("Machine Learning", ("machine learning",)),
    ("Deep Learning", ("deep learning",)),
    ("Data Analysis", ("data analysis", "data analytics")),
    ("Communication", ("communication",)),
    ("Leadership", ("leadership",)),
    ("Project Management", ("project management",)),
    ("ETL", ("etl",)),
    ("Data Pipelines", ("data pipeline", "data pipelines")),
    ("Big Data", ("big data",)),
    ("Data Processing", ("data processing",)),
    ("Data Modeling", ("data modeling", "data modelling")),
    ("Schema Design", ("schema design",)),
    ("Data Structures", ("data structure", "data structures")),
    ("Analytical Skills", ("analytical skills", "analytical")),
    ("Problem Solving", ("problem-solving", "problem solving")),
    ("Performance Tuning", ("performance tuning", "tuning")),
    ("Troubleshooting", ("troubleshooting", "troubleshoot")),
    ("System Design", ("system design", "systems analysis", "architecture")),
    ("Scalable Applications", ("scalable application", "scalable applications")),
    ("Unit Testing", ("unit testing", "unit tests")),
    ("SDLC", ("sdlc", "software development life cycle")),
    ("Linux/Unix", ("linux", "unix")),
    ("Shell Scripting", ("shell scripting", "bash", "shell script")),
    ("Agile/Scrum", ("agile", "scrum")),
    ("JIRA", ("jira",)),
    ("Maven", ("maven",)),
    ("CI/CD", ("continuous integration", "ci/cd")),
    ("Jenkins", ("jenkins",)),
    ("TeamCity", ("teamcity", "team city")),
    ("Real-time Processing", ("real time processing", "real-time processing")),
    ("Low-latency Systems", ("low latency", "low-latency")),
    ("Large-scale Data", ("large data volumes", "large datasets", "large data sets")),
    ("Collaboration", ("collaborate", "collaboration", "global teams")),
    ("Software Testing", ("testing", "test prototypes")),
    ("Data Visualization", ("data visualization", "data visualisation", "charts")),
    ("Git", ("git",)),
    ("REST APIs", ("rest api", "rest apis")),
    ("LangGraph", ("langgraph",)),
)


def extract_skills(job_description: str) -> list[str]:
    """Return recognized skills in their order of appearance in the catalog."""
    text = job_description.casefold()
    skills: list[str] = []
    for skill, aliases in SKILL_ALIASES:
        if any(
            re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text)
            for alias in aliases
        ):
            skills.append(skill)
    return skills
