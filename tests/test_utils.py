from app.utils.formatting import format_feedback
from app.utils.jd_parser import extract_skills
from app.utils.scoring import score_answer


def test_extract_skills_finds_catalog_terms_without_partial_matches() -> None:
    assert extract_skills("Python, SQL and machine learning; not pythonic.") == [
        "Python",
        "SQL",
        "Machine Learning",
    ]


def test_extract_skills_groups_cloud_options_and_data_engineering_skills() -> None:
    assert extract_skills(
        "Build ETL with Python, Pandas, PySpark, SQL and AWS/GCP/Azure; "
        "use data modeling and schema design."
    ) == [
        "Python",
        "Pandas",
        "PySpark",
        "SQL",
        "Cloud Platforms",
        "ETL",
        "Data Modeling",
        "Schema Design",
    ]


def test_extract_skills_recognizes_big_data_job_requirements() -> None:
    skills = extract_skills(
        "Python/Scala, Big Data, HDFS, Map Reduce, YARN, Apache Spark, Hive, "
        "Impala, HBase, Avro, Parquet, CSV, JSON, Linux, shell scripting, "
        "Agile/Scrum, JIRA, No SQL, Maven, Jenkins, Team City, Kafka."
    )

    assert {
        "Python",
        "Scala",
        "Big Data",
        "HDFS",
        "MapReduce",
        "YARN",
        "Apache Spark",
        "Hive",
        "Impala",
        "HBase",
        "Avro",
        "Parquet",
        "CSV",
        "JSON",
        "Linux/Unix",
        "Shell Scripting",
        "Agile/Scrum",
        "JIRA",
        "NoSQL",
        "Maven",
        "Jenkins",
        "TeamCity",
        "Kafka",
    }.issubset(set(skills))
    assert "Cloud Platforms" in extract_skills("familiarity with cloud technologies")
    assert "Containers" in extract_skills("familiarity with container technologies")


def test_extract_skills_recognizes_alteryx_fabric_and_data_pipelines() -> None:
    assert extract_skills(
        "Design data pipelines using Alteryx and Microsoft Fabric."
    ) == ["Alteryx", "Microsoft Fabric", "Data Pipelines"]


def test_score_answer_is_case_insensitive_and_deduplicates_skills() -> None:
    assert score_answer("I use python.", ["Python", "Python", "SQL"]) == (
        50,
        ["Python"],
        ["SQL"],
    )


def test_score_answer_accepts_any_named_cloud_platform_for_grouped_skill() -> None:
    assert score_answer("I deployed the service on AWS.", ["Cloud Platforms"]) == (
        100,
        ["Cloud Platforms"],
        [],
    )


def test_format_feedback_handles_missing_comparison_skills() -> None:
    feedback = format_feedback(0, [], [])

    assert "did not map to a recognized role skill" in feedback
