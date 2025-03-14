from django.urls import path
from .views import get_paper_details
from .views import get_paper_ids_by_field

urlpatterns = [
    path('paper/<str:paper_id>/', get_paper_details, name='get_paper_details'),
    path('papers/computer-science/', get_paper_ids_by_field, name='get_paper_ids_by_field'),
]