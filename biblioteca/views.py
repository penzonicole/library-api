from rest_framework import generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.db.models import Count, Q
from .models import Emprestimo
from .serializers import EmprestimoSerializer, EstatisticasBibliotecaSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        "status": "online",
        "mensagem": "API da Biblioteca ativa com sucesso.",
        "endpoints": {
            "admin": request.build_absolute_uri('/admin/'),
            "login": request.build_absolute_uri('/api/login/'),
            "emprestimos": request.build_absolute_uri('/api/emprestimos/'),
            "estatisticas": request.build_absolute_uri('/api/estatisticas/'),
        }
    })

class EmprestimoListCreateView(generics.ListCreateAPIView):
    serializer_class = EmprestimoSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['data_emprestimo', 'data_devolucao_prevista', 'titulo_livro']

    def get_queryset(self):
        # Garante o isolamento: lista somente os empréstimos do usuário logado
        queryset = Emprestimo.objects.filter(usuario=self.request.user)

        # Filtros via query params
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param.upper())

        categoria_param = self.request.query_params.get('categoria')
        if categoria_param:
            queryset = queryset.filter(categoria=categoria_param.upper())

        return queryset

    def perform_create(self, serializer):
        # Atribui o usuário logado como dono do empréstimo
        serializer.save(usuario=self.request.user)


class EmprestimoDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EmprestimoSerializer

    def get_queryset(self):
        # Se tentar acessar empréstimo de outro usuário, devolve 404
        return Emprestimo.objects.filter(usuario=self.request.user)


class EstatisticasView(APIView):
    def get(self, request):
        qs = Emprestimo.objects.filter(usuario=request.user)
        stats = qs.aggregate(
            total_emprestimos=Count('id'),
            em_andamento=Count('id', filter=Q(status='EMPRESTADO')),
            devolvidos=Count('id', filter=Q(status='DEVOLVIDO')),
            atrasados=Count('id', filter=Q(status='ATRASADO'))
        )
        serializer = EstatisticasBibliotecaSerializer(stats)
        return Response(serializer.data)