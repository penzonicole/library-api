from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from .models import Emprestimo

class BibliotecaAPITest(APITestCase):
    def setUp(self):
        self.ana = User.objects.create_user('ana', password='senha123')
        self.beto = User.objects.create_user('beto', password='senha123')
        self.tok_ana = Token.objects.create(user=self.ana)
        self.tok_beto = Token.objects.create(user=self.beto)

        self.e1 = Emprestimo.objects.create(
            titulo_livro='Dom Casmurro', autor='Machado de Assis', 
            categoria='FICCAO', usuario=self.ana
        )
        self.e2 = Emprestimo.objects.create(
            titulo_livro='Clean Code', autor='Robert C. Martin', 
            categoria='TECNICO', usuario=self.ana, status='DEVOLVIDO'
        )
        self.e3 = Emprestimo.objects.create(
            titulo_livro='Livro do Beto', autor='Autor X', 
            categoria='OUTROS', usuario=self.beto
        )

    def como(self, token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return client

    def test_login_devolve_token(self):
        r = self.client.post(reverse('api-login'), {'username': 'ana', 'password': 'senha123'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['token'], self.tok_ana.key)

    def test_sem_token_401(self):
        self.assertEqual(self.client.get(reverse('emprestimo-lista')).status_code, 401)

    def test_lista_so_do_proprio_usuario(self):
        r = self.como(self.tok_ana).get(reverse('emprestimo-lista'))
        titulos = {item['titulo_livro'] for item in r.data['results']}
        self.assertEqual(titulos, {'Dom Casmurro', 'Clean Code'})

    def test_isolamento_404_em_detalhe_de_outro(self):
        url = reverse('emprestimo-detalhe', args=[self.e1.id])
        # Beto tenta aceder ao empréstimo da Ana e recebe 404
        self.assertEqual(self.como(self.tok_beto).get(url).status_code, 404)
        self.assertEqual(self.como(self.tok_beto).delete(url).status_code, 404)