from rest_framework import serializers
from .models import Emprestimo

class EmprestimoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emprestimo
        fields = '__all__'
        extra_kwargs = {
            'usuario': {'read_only': True}  # O usuário é injetado pelo Token
        }

class EstatisticasBibliotecaSerializer(serializers.Serializer):
    total_emprestimos = serializers.IntegerField()
    em_andamento = serializers.IntegerField()
    devolvidos = serializers.IntegerField()
    atrasados = serializers.IntegerField()