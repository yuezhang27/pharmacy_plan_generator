from django.contrib import admin
from django.urls import path
from careplan import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('api/generate-careplan/', views.generate_careplan, name='generate_careplan'),
    path('api/careplan/<int:careplan_id>/', views.get_careplan, name='get_careplan'),
    path('download-careplan/<int:careplan_id>/', views.download_careplan, name='download_careplan'),
    path('api/search-careplans/', views.search_careplans, name='search_careplans'),
]
