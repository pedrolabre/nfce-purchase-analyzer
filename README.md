# NFC-e Purchase Analyzer

O **NFC-e Purchase Analyzer** é um projeto em fase inicial para uma aplicação desktop local-first de análise de compras a partir de PDFs de NFC-e.

O repositório já contém a estrutura Python mínima do pacote, ainda sem implementação funcional de domínio, parsing, persistência, análise, CLI ou interface gráfica. O desenvolvimento será incremental, começando pelas fundações do domínio, contratos de parsing, persistência local e testes antes da construção da interface gráfica.

## Objetivo

Criar uma ferramenta desktop para importar PDFs originais de NFC-e, extrair dados estruturados de compras, armazenar esses dados localmente e permitir comparação histórica de preços por produto dentro de cada loja.

O foco do MVP é análise de compras de supermercado, com suporte inicial planejado para o layout de NFC-e do mercado Bem Maior.

## Premissas

- Execução 100% local, sem backend web, login, nuvem ou sincronização remota.
- Dados fiscais e arquivos importados permanecem na máquina do usuário.
- Produtos são identificados pelo código interno informado pela própria NFC-e dentro da mesma loja.
- Produtos de lojas diferentes nunca são misturados em análises comparativas.
- O projeto não pretende corrigir inconsistências do cadastro de produtos do estabelecimento.
- O MVP não usará inteligência artificial, LLM, OCR ou fuzzy matching para unificar produtos.

## Escopo Previsto do MVP

- Cadastro local de lojas.
- Importação de PDFs de NFC-e.
- Prévia obrigatória dos dados extraídos antes de gravar qualquer informação.
- Persistência local de compras, itens e produtos.
- Visualização de compras e detalhes dos itens.
- Análise de variação histórica de preços por produto.
- Exportação de resultados analíticos em CSV.

## Stack Prevista

- Python 3.10 ou superior.
- PySide6 para interface desktop.
- pdfplumber para extração de PDFs vetoriais.
- JSON como persistência local canônica.
- CSV para exportação de análises.
- pytest para testes automatizados.

## Testes

Com o `pytest` disponível no ambiente local, execute:

```powershell
python -m pytest
```

O projeto define a configuração mínima do pytest em `pyproject.toml` para o layout `src`.

## Ordem de Desenvolvimento

O desenvolvimento seguirá uma abordagem incremental e rastreável:

1. Documentação pública inicial.
2. Fundações do projeto Python.
3. Modelos e invariantes do domínio.
4. Contratos e implementação inicial de parsing.
5. Persistência local.
6. Motor de análise.
7. CLI de diagnóstico.
8. Interface desktop.
9. Fechamento do MVP.

## Estrutura do Projeto

Estrutura pública atual:

```text
.
├── README.md
├── pyproject.toml
├── src/
│   └── nfce_purchase_analyzer/
│       └── __init__.py
└── tests/
    └── test_package.py
```

Arquivos internos de planejamento e rastreabilidade existem apenas no ambiente local de desenvolvimento e não fazem parte da estrutura pública versionada.
