from semanticscholar import SemanticScholar
from django.http import JsonResponse

sch = SemanticScholar()

def get_paper_details(request, paper_id):
    try:
        paper = sch.get_paper(paper_id)
        paper_data = {
            "title": paper.title,
            "authors": [author.name for author in paper.authors] if paper.authors else [],
            "year": paper.year,
            "abstract": paper.abstract,
            "fields_of_study": paper.fieldsOfStudy,
            "url": paper.url,
        }
        return JsonResponse({"message": "Paper details fetched successfully", "data": paper_data})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
def get_paper_ids_by_field(request):
    try:
        # Step 1: Cari paper dengan query "Computer Science"
        query = "Computer Science"
        papers = sch.search_paper(
            query=query,
            limit=10,  # Batasi jumlah hasil yang diambil
            fields=["paperId", "title", "fieldsOfStudy"]  # Ambil field yang diperlukan
        )

        # Step 2: Filter hasil berdasarkan fieldsOfStudy
        filtered_papers = [
            {
                "paperId": paper.paperId,
                "title": paper.title,
                "fieldsOfStudy": paper.fieldsOfStudy,
            }
            for paper in papers
            if paper.fieldsOfStudy and "Computer Science" in paper.fieldsOfStudy
        ]

        # Step 3: Kembalikan hasil dalam format JSON
        return JsonResponse({
            "message": f"Papers with field of study 'Computer Science' fetched successfully",
            "data": filtered_papers,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
