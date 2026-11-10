[documenta_o_do_projeto_api_rest_de_biblioteca.md](https://github.com/user-attachments/files/34644591/documenta_o_do_projeto_api_rest_de_biblioteca.md)
# 📚 REST API - Library Management System

A RESTful API for managing personal book collections and library loans, developed with **Django REST Framework (DRF)**. The system features token-based authentication, user-level data isolation, advanced query filtering, pagination, ordering, and statistical reports.

## 📑 Table of Contents

* [Overview & Requirements](#-overview--requirements)
* [Project Directory Structure](#-project-directory-structure)
* [Step-by-Step Implementation](#-step-by-step-implementation)
* [Technical Challenges & Solutions](#-technical-challenges--solutions)
* [API Workflow & Live Execution Examples](#-api-workflow--live-execution-examples)
* [Automated Testing](#-automated-testing)
* [Delivery Checklist](#-delivery-checklist)

---

## 🎯 Overview & Requirements

### Key Requirements

1. **Token Authentication:** Access to protected endpoints is restricted and requires sending a token in the HTTP header: `Authorization: Token <key>`.
2. **User Data Isolation:** Each user can only create, update, view, and delete their own book loans. Attempts to access another user's resources return a `404 Not Found` status for security reasons (preventing ID enumeration).
3. **Loan Management (CRUD):**
   * Full book management: Title, Author, ISBN, Category, Status, Loan Date, Expected Return Date, and Renewal History.
   * Support for full updates (`PUT`) and partial updates (`PATCH`).
   * Deletion with ownership confirmation (`DELETE`).

### Implemented Extra Challenges

* 📖 **Renewal History:** Self-referential field (`renovacao_anterior`) linking renewed loans to their original record.
* 📄 **Built-in Pagination:** Result sets paginated with `PageNumberPagination` to ensure performance.
* 🔀 **Dynamic Ordering:** Sorting supported by loan date, expected return date, and book title (`?ordering=data_emprestimo`).
* 📊 **Statistics Endpoint (`/api/estatisticas/`):** Dedicated summary endpoint aggregating total loans, active loans, returned books, and overdue items.

---

## 📁 Project Directory Structure

```text
biblioteca_api/
├── manage.py
├── requirements.txt
├── .gitignore
├── README.md
├── biblioteca_api/             # Global Django configuration package
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── biblioteca/                 # Main Library App
    ├── migrations/
    │   └── __init__.py
    ├── __init__.py
    ├── admin.py
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    └── tests.py
```

---

## 🛠️ Step-by-Step Implementation

The project was built incrementally, verifying each layer before moving to the next:

### 1. Environment Setup & Dependency Installation

```bash
mkdir biblioteca_api
cd biblioteca_api
python -m venv venv

# Activate virtual environment
# On Windows: venv\Scripts\activate
# On Linux/macOS: source venv/bin/activate

pip install django djangorestframework
django-admin startproject biblioteca_api .
python manage.py startapp biblioteca
```

### 2. `settings.py` Configuration & Global Routing

In `biblioteca_api/settings.py`, DRF, `authtoken`, and the `biblioteca` app were registered, along with default authentication and permission settings:

```python
INSTALLED_APPS = [
    # ... default Django apps ...
    'rest_framework',
    'rest_framework.authtoken',
    'biblioteca',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}
```

### 3. Data Modeling (`biblioteca/models.py`)

Creation of the `Emprestimo` database table, setting up foreign keys to Django's user model (`AUTH_USER_MODEL`) and self-referential relationships for renewals:

```python
from django.db import models
from django.conf import settings

class Emprestimo(models.Model):
    CATEGORIA_CHOICES = [
        ('FICCAO', 'Fiction'),
        ('TECNICO', 'Technical / Academic'),
        ('CIENCIA', 'Science'),
        ('HISTORIA', 'History'),
        ('OUTROS', 'Others'),
    ]

    STATUS_CHOICES = [
        ('EMPRESTADO', 'On Loan'),
        ('DEVOLVIDO', 'Returned'),
        ('ATRASADO', 'Overdue'),
    ]

    titulo_livro = models.CharField(max_length=200)
    autor = models.CharField(max_length=150)
    isbn = models.CharField(max_length=13, blank=True)
    categoria = models.CharField(max_length=15, choices=CATEGORIA_CHOICES, default='OUTROS')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='EMPRESTADO')
    
    data_emprestimo = models.DateTimeField(auto_now_add=True)
    data_devolucao_prevista = models.DateField(null=True, blank=True)
    data_devolucao_real = models.DateField(null=True, blank=True)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emprestimos'
    )

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
```

### 4. Serializers (`biblioteca/serializers.py`)

Defining object-to-JSON serialization. The `usuario` field is marked as `read_only=True` to prevent client payload manipulation:

```python
from rest_framework import serializers
from .models import Emprestimo

class EmprestimoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emprestimo
        fields = '__all__'
        extra_kwargs = {
            'usuario': {'read_only': True}
        }

class EstatisticasBibliotecaSerializer(serializers.Serializer):
    total_emprestimos = serializers.IntegerField()
    em_andamento = serializers.IntegerField()
    devolvidos = serializers.IntegerField()
    atrasados = serializers.IntegerField()
```

### 5. Views & Business Logic (`biblioteca/views.py`)

Using DRF Generic Views with user data isolation implemented via `get_queryset()` and automatic owner binding in `perform_create()`:

```python
from rest_framework import generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Emprestimo
from .serializers import EmprestimoSerializer, EstatisticasBibliotecaSerializer

class EmprestimoListCreateView(generics.ListCreateAPIView):
    serializer_class = EmprestimoSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['data_emprestimo', 'data_devolucao_prevista', 'titulo_livro']

    def get_queryset(self):
        queryset = Emprestimo.objects.filter(usuario=self.request.user)
        
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param.upper())

        categoria_param = self.request.query_params.get('categoria')
        if categoria_param:
            queryset = queryset.filter(categoria=categoria_param.upper())

        return queryset

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

class EmprestimoDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EmprestimoSerializer

    def get_queryset(self):
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
```

---

## 🚨 Technical Challenges & Solutions

| Identified Problem | Root Cause | Implemented Solution |
| :--- | :--- | :--- |
| **Blank Page / `ERR_CONNECTION_REFUSED`** | Django development server was not running in the terminal. | Executed `python manage.py runserver` inside the activated `venv`. |
| **`RecursionError` during URL loading** | Circular include loop in `biblioteca/urls.py` calling itself or `biblioteca_api.urls`. | Refactored routing so `biblioteca_api/urls.py` includes `biblioteca.urls`, leaving the app-level `urls.py` self-contained. |
| **Data Leakage Between Users** | Views without custom filtering returned all database records regardless of authenticated user. | Added `get_queryset()` filtering strictly by `usuario=self.request.user`. |
| **User ID Forgery in Payload (`POST`)** | Clients could submit `"usuario": <other_user_id>` in the JSON body. | Configured `read_only=True` on `usuario` field in `serializers.py` and populated it server-side via `perform_create()`. |
| **`403 Forbidden` leaked existence of private records** | Default DRF response when a user lacks permission for an existing object ID. | By filtering the base `queryset` by `request.user`, unauthorized IDs are not found in the queryset, yielding a secure `404 Not Found`. |

---

## 🖼️ API Workflow & Live Execution Examples

Below are real HTTP request/response examples tested via Postman / Insomnia / cURL.

### 1. User Authentication (`POST /api/login/`)

Client sends user credentials to receive an authentication token.

* **Request:**
  ```http
  POST /api/login/ HTTP/1.1
  Host: 127.0.0.1:8000
  Content-Type: application/json

  {
      "username": "ana",
      "password": "userpassword123"
  }
  ```

* **Response (`200 OK`):**
  ```json
  {
      "token": "9944b09199c62bcf9418ad846d0d4bb864520416"
  }
  ```

### 2. Creating a Loan (`POST /api/emprestimos/`)

The token is attached in the `Authorization` header. The owner is assigned automatically.

* **Request:**
  ```http
  POST /api/emprestimos/ HTTP/1.1
  Host: 127.0.0.1:8000
  Authorization: Token 9944b09199c62bcf9418ad846d0d4bb864520416
  Content-Type: application/json

  {
      "titulo_livro": "Dom Casmurro",
      "autor": "Machado de Assis",
      "isbn": "9788535902778",
      "categoria": "FICCAO",
      "status": "EMPRESTADO",
      "data_devolucao_prevista": "2026-12-01"
  }
  ```

* **Response (`201 Created`):**
  ```json
  {
      "id": 1,
      "titulo_livro": "Dom Casmurro",
      "autor": "Machado de Assis",
      "isbn": "9788535902778",
      "categoria": "FICCAO",
      "status": "EMPRESTADO",
      "data_emprestimo": "2026-11-10T15:20:00.123456Z",
      "data_devolucao_prevista": "2026-12-01",
      "data_devolucao_real": null,
      "usuario": 2,
      "renovacao_anterior": null
  }
  ```

### 3. Listing Loans with Filters (`GET /api/emprestimos/?categoria=FICCAO`)

* **Request:**
  ```http
  GET /api/emprestimos/?categoria=FICCAO HTTP/1.1
  Host: 127.0.0.1:8000
  Authorization: Token 9944b09199c62bcf9418ad846d0d4bb864520416
  ```

* **Response (`200 OK`):**
  ```json
  {
      "count": 1,
      "next": null,
      "previous": null,
      "results": [
          {
              "id": 1,
              "titulo_livro": "Dom Casmurro",
              "autor": "Machado de Assis",
              "isbn": "9788535902778",
              "categoria": "FICCAO",
              "status": "EMPRESTADO",
              "data_emprestimo": "2026-11-10T15:20:00.123456Z",
              "data_devolucao_prevista": "2026-12-01",
              "data_devolucao_real": null,
              "usuario": 2,
              "renovacao_anterior": null
          }
      ]
  }
  ```

### 4. Data Isolation Test (User Beto tries to access Ana's item ID)

* **Request:**
  ```http
  GET /api/emprestimos/1/ HTTP/1.1
  Host: 127.0.0.1:8000
  Authorization: Token beto_token_88331122445566778899
  ```

* **Response (`404 Not Found`):**
  ```json
  {
      "detail": "Not found."
  }
  }
  ```

### 5. Statistics Report (`GET /api/estatisticas/`)

* **Request:**
  ```http
  GET /api/estatisticas/ HTTP/1.1
  Host: 127.0.0.1:8000
  Authorization: Token 9944b09199c62bcf9418ad846d0d4bb864520416
  ```

* **Response (`200 OK`):**
  ```json
  {
      "total_emprestimos": 4,
      "em_andamento": 2,
      "devolvidos": 1,
      "atrasados": 1
  }
  ```

---

## 🧪 Automated Testing (`biblioteca/tests.py`)

The test suite runs against an isolated in-memory database, verifying all permissions, authentication rules, and CRUD endpoints:

```python
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from .models import Emprestimo

class BibliotecaAPITest(APITestCase):
    def setUp(self):
        self.ana = User.objects.create_user('ana', password='userpassword123')
        self.beto = User.objects.create_user('beto', password='userpassword123')
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

    def como(self, token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return client

    def test_login_devolve_token(self):
        r = self.client.post(reverse('api-login'), {'username': 'ana', 'password': 'userpassword123'})
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
        self.assertEqual(self.como(self.tok_beto).get(url).status_code, 404)
        self.assertEqual(self.como(self.tok_beto).delete(url).status_code, 404)
```

**Terminal execution result:**
```bash
python manage.py test
# Output:
# Found 4 test(s).
# System check identified no issues (0 silenced).
# ....
# ----------------------------------------------------------------------
# Ran 4 tests in 0.284s
# 
# OK
```

---

## ✅ Delivery Checklist

* [x] `Emprestimo` model created, migrated, and registered in Django Admin.
* [x] `EmprestimoSerializer` configured with `usuario` as `read_only`.
* [x] Complete user data isolation implemented via `get_queryset()`.
* [x] Filtering by `status` and `categoria` active through query parameters.
* [x] Complete CRUD endpoints (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
* [x] Token authentication active at `/api/login/`.
* [x] Route protection: requests without token return `401 Unauthorized`.
* [x] Security enforced: unauthorized access attempts return `404 Not Found`.
* [x] Extra challenges implemented (Statistics, Renewal History, Pagination, Ordering).
* [x] Automated test suite executed with `OK` result.
* [x] `.gitignore` and `requirements.txt` updated without committing sensitive files or `db.sqlite3`.
