from django.contrib import admin
from django.urls import path
from careplan import views

# Django是一个Python Web框架
# urls.py ： 这里放django框架下的所有path（采用RESTful API模式）
# 格式为：
"""
- urlpatterns = [path(), path()...] -> 这里放所有path
- path的格式：path(路径， 对应的views里的方法， name)
- 这个path里的name：用于 URL 反向解析（reverse() / {% url %}）
"""
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('api/generate-careplan/', views.generate_careplan, name='generate_careplan'),
    path('api/intake/pharmacorp/', views.intake_pharmacorp, name='intake_pharmacorp'),
    path('api/careplan/<int:careplan_id>/', views.get_careplan, name='get_careplan'),
    path('api/careplan/<int:careplan_id>/status/', views.careplan_status, name='careplan_status'),
    path('download-careplan/<int:careplan_id>/', views.download_careplan, name='download_careplan'),
    path('api/search-careplans/', views.search_careplans, name='search_careplans'),
]
