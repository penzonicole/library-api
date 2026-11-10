from django.contrib import admin
from .models import Emprestimo

@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ('titulo_livro', 'autor', 'usuario', 'categoria', 'status', 'data_devolucao_prevista')
    list_filter = ('status', 'categoria')
    search_fields = ('titulo_livro', 'autor', 'isbn')