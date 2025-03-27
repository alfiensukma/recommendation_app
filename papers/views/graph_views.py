import os
import csv
from langchain_community.graphs import Neo4jGraph
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "papers", "data-csv")  # Sesuaikan dengan struktur di container
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
    query = f"""
    LOAD CSV WITH HEADERS FROM 'file:///{os.path.basename(file_path)}' AS row
    MERGE (p:Paper {{paper_id: row.paper_id}})
    SET p.title = row.title,
        p.authors = split(coalesce(row.authors, ''), ', '),
        p.year = toInteger(row.year),
        p.publication_date = row.publication_date,
        p.abstract = row.abstract,
        p.url = row.url,
        p.external_ids = row.external_ids,
        p.fields_of_study = split(row.fields_of_study, ','),
        p.reference_count = toInteger(row.reference_count),
        p.embedding = row.embedding
    {'SET p.reference_id = split(row.reference_id, ",")' if not is_reference else ''}
    """
    graph.query(query)

def import_references(graph):
    query = f"""
    LOAD CSV WITH HEADERS FROM 'file:///{os.path.basename(REFERENCES_PATH)}' AS row
    MATCH (source:Paper {{paper_id: row.source_id}})
    MATCH (target:Paper {{paper_id: row.target_id}})
    MERGE (source)-[:REFERENCES]->(target)
    """
    graph.query(query)

def import_to_neo4j(graph):
    clear_neo4j(graph)
    import_papers(graph, PAPERS_PATH)
    if os.path.exists(PAPER_REFERENCES_PATH):
        import_papers(graph, PAPER_REFERENCES_PATH, is_reference=True)
    if os.path.exists(REFERENCES_PATH):
        import_references(graph)

@csrf_exempt
def generate_knowledge_graph(request):
    try:
        if request.method != "GET":
            return JsonResponse({"error": "Method not allowed"}, status=405)

        if not os.path.exists(PAPERS_PATH):
            return JsonResponse({"error": f"File not found: {PAPERS_PATH}"}, status=400)

        # Inisialisasi Neo4jGraph di dalam fungsi
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
            "csv_files": {
                "papers": PAPERS_PATH,
                "paper_references": PAPER_REFERENCES_PATH,
                "references": REFERENCES_PATH
            }
        }, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)