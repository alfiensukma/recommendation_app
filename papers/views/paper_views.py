import os
import asyncio
import csv
from semanticscholar import SemanticScholar
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

sch = SemanticScholar()
CSV_PATH = "papers/data-csv"
PAPERS_PATH = os.path.join(CSV_PATH, "papers.csv")
PAPER_REFERENCES_PATH = os.path.join(CSV_PATH, "paper-references.csv")
REFERENCES_PATH = os.path.join(CSV_PATH, "references.csv")

if not os.path.exists(CSV_PATH):
    os.makedirs(CSV_PATH)

def save_to_csv(file_path, data, fieldnames, mode='w'):
    with open(file_path, mode=mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, extrasaction='ignore')
        if mode == 'w' or (mode == 'a' and os.stat(file_path).st_size == 0):
            writer.writeheader()
        for row in data:
            csv_row = {key: str(row.get(key, '')) for key in fieldnames}
            if 'authors' in csv_row and row['authors']:
                csv_row['authors'] = ', '.join([author for author in row['authors'] if author])
            if 'reference_id' in csv_row:
                csv_row['reference_id'] = ','.join(csv_row['reference_id']) if csv_row['reference_id'] else ''
            writer.writerow(csv_row)

# Helper function to create paper info dictionary
def create_paper_info(paper, include_references=False, reference_limit=None):
    paper_info = {
        "paper_id": str(paper.paperId or ""),
        "external_ids": str(paper.externalIds or ""),
        "fields_of_study": ','.join(paper.fieldsOfStudy or []),
        "title": str(paper.title or ""),
        "authors": [str(author.name).strip() for author in (paper.authors or [])],
        "year": str(paper.year or ""),
        "publication_date": str(paper.publicationDate or ""),
        "abstract": str(paper.abstract or ""),
        "url": str(paper.url or ""),
        "embedding": str(paper.embedding or ""),
        "referenceCount": str(paper.referenceCount or 0),
    }
    if include_references and hasattr(paper, 'references'):
        refs = paper.references or []
        ref_ids = [ref.paperId for ref in refs if ref.paperId]
        paper_info["reference_id"] = ref_ids[:reference_limit] if reference_limit is not None and reference_limit >= 0 else ref_ids
    return paper_info

def get_paper_detail(request, paper_id):
    try:
        paper = sch.get_paper(paper_id)
        return JsonResponse({
            "message": "Paper details fetched successfully",
            "data": create_paper_info(paper)
        }, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_paper(request):
    try:
        if request.method != "GET":
            return JsonResponse({"error": "Method not allowed"}, status=405)

        query = request.GET.get('query', '')
        min_year = int(request.GET.get('min_year', 2020)) # tahun minimum (contoh "2020-", artinya tahun 2020 ke atas)
        fields_of_study = request.GET.get('fields_of_study', 'Computer Science')
        reference_limit = request.GET.get('reference_limit', 20) # limit untuk mendapatkan paper referensi dari setiap paper
        bulk = request.GET.get('bulk', 'false').lower() == 'true' # pencarian secara = relevance search (bulk false) atau bulk retrieval search (bulk true)
        limit = int(request.GET.get('limit', 100)) #  bulk mode limit = 1000, relevance mode limit = 100
        
        reference_limit = int(reference_limit) if reference_limit is not None else None

        # get data paper from Semantic Scholar
        results = sch.search_paper(
            query, year=f"{min_year}-", limit=limit,
            fields_of_study=[fields_of_study],
            fields=['paperId', 'title', 'authors', 'year', 'publicationDate', 'fieldsOfStudy', 'abstract', 'url', 'references', 'externalIds', 'embedding', 'referenceCount'],
        )

        if not results:
            return JsonResponse({"message": "No papers found", "data": []}, status=200)

        paper_data = [
            create_paper_info(paper, include_references=True, reference_limit=reference_limit)
            for paper in results if paper.year and paper.year >= min_year
        ][:limit]
        references_list = [
            {"source_id": paper["paper_id"], "target_id": ref_id}
            for paper in paper_data for ref_id in paper.get("reference_id", [])
        ]

        # save data paper to CSV
        paper_fieldnames = ["paper_id", "external_ids", "title", "fields_of_study", "authors", "year", "publication_date", "abstract", "url", "reference_count", "embedding"]
        save_to_csv(PAPERS_PATH, paper_data, paper_fieldnames, mode='w')

        # save data references to CSV
        reference_fieldnames = ["source_id", "target_id"]
        save_to_csv(REFERENCES_PATH, references_list, reference_fieldnames, mode='w')

        return JsonResponse({
            "message": "Paper fetched successfully, data saved to CSV",
            "data": paper_data,
            "papers_saved": len(paper_data),
            "references_saved": len(references_list),
            "csv_files": {"papers": PAPERS_PATH, "references": REFERENCES_PATH},
            "mode": "bulk" if bulk else "relevance",
        }, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

async def get_paper_reference(target_id):
    try:
        paper = await asyncio.to_thread(sch.get_paper, target_id, 
            fields=['paperId', 'title', 'authors', 'year', 'publicationDate', 'fieldsOfStudy', 'abstract', 'url', 'externalIds', 'referenceCount', 'embedding'])
        return create_paper_info(paper)
    except Exception as e:
        print(f"Error fetching paper {target_id}: {e}")
        return None

# Fetch papers by reference IDs (async)
@csrf_exempt
def fetch_papers_by_reference_ids(request):
    try:
        if request.method != "GET":
            return JsonResponse({"error": "Method not allowed"}, status=405)

        if not os.path.exists(REFERENCES_PATH):
            return JsonResponse({"error": f"File not found: {REFERENCES_PATH}"}, status=400)

        with open(REFERENCES_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            target_ids = {row['target_id'] for row in reader if row['target_id']}

        if not target_ids:
            return JsonResponse({"error": "No valid reference IDs found in references.csv"}, status=400)

        async def fetch_all():
            tasks = [get_paper_reference(target_id) for target_id in target_ids]
            return await asyncio.gather(*tasks)

        paper_data = asyncio.run(fetch_all())
        paper_data = [paper for paper in paper_data if paper is not None]

        # save data to CSV
        if paper_data:
            paper_fieldnames = ["paper_id", "external_ids", "title", "fields_of_study", "authors", "year", "publication_date", "abstract", "url", "reference_count", "embedding"]
            save_to_csv(PAPER_REFERENCES_PATH, paper_data, paper_fieldnames, mode='a')

        return JsonResponse({
            "message": "Papers fetched by reference IDs successfully, data appended to paper-references.csv",
            "data": paper_data,
            "papers_fetched": len(paper_data),
            "csv_file": PAPER_REFERENCES_PATH
        }, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)