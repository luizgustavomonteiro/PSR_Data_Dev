from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name ="home"),
    path('maps', views.maps, name = "maps"),
    path('graphics', views.graphs, name = "graphics"),
    path('developmentteam', views.team, name = 'developmentteam'), 
    path('base', views.base, name ="base"),
]