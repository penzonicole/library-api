from django.conf import settings
from django.db import models

class Emprestimo(models.Model):
    CATEGORIA_CHOICES = [
        ('FICCAO', 'Ficção'),
        ('TECNICO', 'Técnico / Acadêmico'),
        ('CIENCIA', 'Ciência'),
        ('HISTORIA', 'História'),
        ('OUTROS', 'Outros'),
    ]

    STATUS_CHOICES = [
        ('EMPRESTADO', 'Emprestado'),
        ('DEVOLVIDO', 'Devolvido'),
        ('ATRASADO', 'Atrasado'),
    ]

    titulo_livro = models.CharField(max_length=200)
    autor = models.CharField(max_length=150)
    isbn = models.CharField(max_length=13, blank=True)
    categoria = models.CharField(max_length=15, choices=CATEGORIA_CHOICES, default='OUTROS')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='EMPRESTADO')
    
    data_emprestimo = models.DateTimeField(auto_now_add=True)
    data_devolucao_prevista = models.DateField(null=True, blank=True)
    data_devolucao_real = models.DateField(null=True, blank=True)

    # Dono do empréstimo (isolamento por usuário)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emprestimos'
    )

    # Desafio extra: auto-relacionamento para controle de renovação anterior
    renovacao_anterior = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='renovacoes'
    )

    class Meta:
        ordering = ['-data_emprestimo', '-id']

    def __str__(self):
        return f"{self.titulo_livro} - {self.usuario.username}"