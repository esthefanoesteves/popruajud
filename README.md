# PopRuaJud · Controle de Acesso

Credenciamento com reconhecimento facial pelo celular para liberar o acesso aos setores e controlar as entregas de alimentos e roupas nos mutirões Pop Rua Jud do TRF3 e da PRR3.

Trabalho de Laboratório de Engenharia de Software (IES301), FATEC-SP, 2026.2. Autor: Esthefano Guimarães Esteves.

## Stack

- Python 3.12+ com Django 5.2 LTS
- PostgreSQL (SQLite no desenvolvimento rápido)
- OpenCV para o rosto: YuNet detecta, SFace gera o modelo facial. Modelos abertos, sem custo de licença.
- Docker Compose para subir banco e aplicação juntos

## Como rodar no Windows

```powershell
git clone https://github.com/esthefanoesteves/popruajud.git
cd popruajud
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
python scripts\baixar_modelos.py
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra http://localhost:8000/admin e entre com o usuário criado.

### Com Docker

```powershell
docker compose up --build
docker compose exec web python manage.py createsuperuser
```

## Testes

```powershell
pytest
```

O teste com os modelos faciais reais roda quando os `.onnx` estão em `modelos/` e a variável `FACE_IMAGEM_TESTE` aponta para uma foto com um rosto:

```powershell
$env:FACE_IMAGEM_TESTE="C:\caminho\foto.jpg"; pytest tests\test_face.py
```

## Onde está cada requisito

| Pasta | Setor | Requisitos |
|---|---|---|
| `mutirao/` | Gestão do mutirão: evento, postos, cotas, perfis | RF-01, RF-02 |
| `credenciamento/` | Credenciamento: dados mínimos, consentimento, foto, QR, triagem | RF-03 a RF-07, RD-01, RD-02, RD-05, RD-06, RNF-10 |
| `acesso/` | Reconhecimento facial, entrada nos setores, atendimentos | RF-08, RF-09, RF-14, RD-03, RD-04, RNF-09 |
| `entregas/` | Alimentos e roupas: cotas, bloqueio da 2ª retirada, estoque | RF-10 a RF-13 |
| `auditoria/` | Trilha de auditoria somente de inclusão | RF-17, RNF-12 |
| `core/cripto.py` | Fotos e modelos faciais cifrados em AES-256 | RNF-08 |
| `config/settings.py` | Senhas com bcrypt, sessão de 15 min, HTTPS | RNF-08 |

## Situação

Pronto nesta versão: modelo de dados dos quatro setores, regras de cota e bloqueio da segunda retirada, cifragem dos dados faciais, trilha de auditoria imutável, reconhecimento facial com OpenCV e painel administrativo.

Próximas etapas, conforme o cronograma (item 3.b):

- Telas do celular para os postos (item 3.g)
- Credencial com QR para impressão (RF-06)
- Painel em tempo real e relatório final do CNJ (RF-15, RF-16)
- Eliminação dos dados faciais ao encerrar o mutirão (RF-18)
- Operação sem internet e sincronização com a nuvem (RNF-04)

## Câmera no celular

O navegador só libera a câmera em páginas HTTPS (ou em `localhost`). Para testar no celular pela rede local, o servidor precisa de HTTPS.

## Privacidade

Fotos, modelos faciais, o arquivo `.env` e os modelos `.onnx` nunca entram no repositório. O reconhecimento facial só compara o rosto com pessoas credenciadas que consentiram (RD-02, RD-03) e, abaixo do limiar, o operador decide (RD-04).
