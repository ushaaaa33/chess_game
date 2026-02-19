from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    path('',                    views.index,    name='index'),
    path('new/',                views.new_game, name='new_game'),
    path('<int:game_id>/moves/', views.get_moves, name='get_moves'),
    path('<int:game_id>/move/',  views.make_move, name='make_move'),
]