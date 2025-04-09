import json
from neo4j import GraphDatabase

# Load JSON data
with open("papers-json.json", "r", encoding="utf-8") as f:
    papers = json.load(f)["data"]

# Setup Neo4j connection
uri = "bolt://localhost:7687"
user = "neo4j"
password = "password"

driver = GraphDatabase.driver(uri, auth=(user, password))

def clear_neo4j(graph):
    graph.query("MATCH (n) DETACH DELETE n")

def import_paper(tx, paper):
    tx.run("""
        MERGE (p:Paper {paperId: $paperId})
        SET p.title = $title,
            p.abstract = $abstract,
            p.url = $url,
            p.year = $year,
            p.referenceCount = $referenceCount,
            p.citationCount = $citationCount,
            p.influentialCitationCount = $influentialCitationCount,
            p.publicationDate = $publicationDate,
            p.fieldsOfStudy = $fieldsOfStudy,
            p.externalIds = $externalIds,
            p.embedding = $embedding
    """, 
    paperId=paper.get("paperId"),
    title=paper.get("title"),
    abstract=paper.get("abstract"),
    url=paper.get("url"),
    year=paper.get("year"),
    referenceCount=paper.get("referenceCount", 0),
    citationCount=paper.get("citationCount", 0),
    influentialCitationCount=paper.get("influentialCitationCount", 0),
    publicationDate=paper.get("publicationDate"),
    fieldsOfStudy=paper.get("fieldsOfStudy", []),
    externalIds=paper.get("externalIds", {}),
    embedding=paper.get("embedding", [])
    )

with driver.session() as session:
    session.write_transaction(clear_neo4j)
    for paper in papers:
        session.write_transaction(import_paper, paper)

driver.close()