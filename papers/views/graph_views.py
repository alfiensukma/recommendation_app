import os
import csv
from langchain_community.graphs import Neo4jGraph
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data-csv")
PAPERS_PATH = os.path.join(DATA_DIR, "papers.csv")
PAPER_REFERENCES_PATH = os.path.join(DATA_DIR, "paper-references.csv")
REFERENCES_PATH = os.path.join(DATA_DIR, "references.csv")

def get_neo4j_graph():
    return Neo4jGraph(
        url=os.getenv('NEO4J_URI', 'bolt://neo4j:7687'),
        username=os.getenv('NEO4J_USERNAME', 'neo4j'),
        password=os.getenv('NEO4J_PASSWORD', 'alfien0310')
    )

def count_csv_rows(file_path):
    if not os.path.exists(file_path):
        return 0
    with open(file_path, mode='r', encoding='utf-8') as f:
        return sum(1 for row in csv.DictReader(f))

def clear_neo4j(graph):
    graph.query("MATCH (n) DETACH DELETE n")

def import_papers(graph, file_path, is_reference=False):
    # Query untuk import Paper dan Author serta relasi dasar
    query = f"""
    LOAD CSV WITH HEADERS FROM 'file:///{os.path.basename(file_path)}' AS row
    MERGE (p:Paper {{paperId: row.paperId}})
    SET p.corpusId = row.corpusId,
        p.externalIds = row.externalIds,
        p.title = row.title,
        p.authors = [author IN apoc.convert.fromJsonList(row.authors) | author.name],
        p.year = toInteger(row.year),
        p.abstract = row.abstract,
        p.url = row.url,
        p.publicationDate = row.publicationDate,
        p.fieldsOfStudy = split(row.fieldsOfStudy, ';'),
        p.s2FieldsOfStudy = split(row.s2FieldsOfStudy, ';'),
        p.venue = row.venue,
        p.publicationVenue = row.publicationVenue,
        p.citationCount = toInteger(row.citationCount),
        p.influentialCitationCount = toInteger(row.influentialCitationCount),
        p.publicationTypes = split(row.publicationTypes, ';'),
        p.journal = row.journal,
        p.citationStyles = row.citationStyles,
        p.embedding = apoc.convert.fromJsonList(row.embedding),
        p.referenceCount = toInteger(row.referenceCount)
    {'SET p.reference_id = split(row.reference_id, ";")' if not is_reference else ''}

    WITH p, apoc.convert.fromJsonList(row.authors) AS authors
    UNWIND authors AS author
    MERGE (a:Author {{authorId: author.authorId}})
    SET a.name = author.name
    MERGE (p)-[:AUTHORED_BY]->(a)
    
    WITH p, authors
    UNWIND apoc.coll.combinations(authors, 2, 2) AS pair
    WITH p, pair[0] AS a1, pair[1] AS a2
    WHERE a1.authorId < a2.authorId
    MERGE (author1:Author {{authorId: a1.authorId}})
    MERGE (author2:Author {{authorId: a2.authorId}})
    MERGE (author1)-[r:COLLABORATED_WITH]->(author2)
    ON CREATE SET r.weight = 1, r.papers = [p.paperId]
    ON MATCH SET r.weight = r.weight + 1, r.papers = r.papers + p.paperId
    """
    graph.query(query)

def import_references(graph):
    query = f"""
    LOAD CSV WITH HEADERS FROM 'file:///{os.path.basename(REFERENCES_PATH)}' AS row
    MATCH (source:Paper {{paperId: row.source_id}})
    MATCH (target:Paper {{paperId: row.target_id}})
    MERGE (source)-[:REFERENCES]->(target)
    """
    graph.query(query)

def import_to_neo4j(graph):
    clear_neo4j(graph)
    import_papers(graph, PAPERS_PATH)
    # if os.path.exists(PAPER_REFERENCES_PATH):
    #     import_papers(graph, PAPER_REFERENCES_PATH, is_reference=True)
    # if os.path.exists(REFERENCES_PATH):
    #     import_references(graph)

@csrf_exempt
def generate_knowledge_graph(request):
    try:
        if request.method != "GET":
            return JsonResponse({"error": "Method not allowed"}, status=405)

        graph = get_neo4j_graph()
        
        # Impor data ke Neo4j
        import_to_neo4j(graph)

        # Hitung jumlah baris
        papers_count = count_csv_rows(PAPERS_PATH)
        paper_references_count = count_csv_rows(PAPER_REFERENCES_PATH)
        references_count = count_csv_rows(REFERENCES_PATH)

        return JsonResponse({
            "message": "Knowledge graph generated successfully",
            "papers_processed": papers_count,
            "paper_references_processed": paper_references_count,
            "references_processed": references_count,
        }, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)