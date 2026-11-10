from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_root, name='biblioteca-root'),
    path('emprestimos/', views.EmprestimoListCreateView.as_view(), name='emprestimo-lista'),
    path('emprestimos/<int:pk>/', views.EmprestimoDetailView.as_view(), name='emprestimo-detalhe'),
    path('estatisticas/', views.EstatisticasView.as_view(), name='emprestimo-estatisticas'),
]