# Eleições Roblox 2026 🗳️

Site de simulação eleitoral com o design do painel de resultados (inspirado na tela enviada),
com **banco de dados SQLite**, envio de candidatos (foto por **upload** ou por **link**) e envio
de resultados pelo próprio site.

## Como rodar

É preciso ter **Python 3.9+** instalado. Depois:

```bash
# 1. instalar a dependência
pip install -r requirements.txt

# 2. iniciar o site
python app.py
```

Abra **http://127.0.0.1:5000** no navegador. Pronto!

- No Windows: dê um duplo clique em `iniciar.bat` (instala a dependência e sobe o site).
- No Linux/Mac: `./iniciar.sh`.
- O banco de dados é criado automaticamente em `database/eleicoes.db` na primeira execução
  (e já vem preenchido com dados de exemplo).

## O que cada página faz

| Página (menu) | O que faz |
| --- | --- |
| **Resultados** | Painel principal (igual à tela de referência): Dados Gerais, Votação, Eleitorado geral e cards dos candidatos com porcentagem, votos, foto e situação (Eleito / Não eleito). Botões `1º`/`2º` trocam o turno; `Atualizar` recarrega; a lupa filtra candidatos pelo nome; o `i` mostra informações. |
| **Perfis Salvos** | Lista todos os candidatos cadastrados, com **Editar** e **Excluir**. |
| **Resumo Geral** | Balanço por turno (total de votos, nominais, seções totalizadas, mais votado) e classificação geral dos candidatos. |
| **Arquivos de Urna** | **Exportar** todos os dados em JSON, **importar por arquivo** JSON e **importar por link** (URL de um JSON publicado na internet). Também expõe a API em `/api/resultados`. |

### Enviar candidato (foto por upload ou link)

Em **Perfis Salvos → + Enviar candidato**: nome, partido, número, cargo, eleição, turno,
votos, eleito e a foto — que pode ser:

1. **Upload de arquivo** (PNG, JPG, GIF ou WEBP até 8 MB) — fica salvo em `media/fotos/`; ou
2. **Link (URL)** de uma imagem hospedada em qualquer lugar.

Se os dois forem preenchidos, o arquivo enviado tem prioridade. Quem não tem foto mostra
as iniciais do nome.

### Enviar resultados

Em **Resumo Geral → Enviar resultados** (ou `/resultados/enviar`): informe os Dados Gerais do
turno (vagas, seções, totalizadas, eleitorado, brancos, nulos, anulados, sub judice, data da
última atualização) e os votos de cada candidato. Tudo é recalculado automaticamente
(percentuais, comparecimento, abstenção, barra de totalização).

## Banco de dados

SQLite, arquivo `database/eleicoes.db` (criado a partir de `schema.sql`):

- **eleicoes** — id, nome, ano;
- **candidatos** — eleição, turno, cargo, nome, partido, número, foto (arquivo ou URL),
  votos, eleito;
- **dados_gerais** — por eleição + turno: vagas, seções, totalizadas, eleitorado, brancos,
  nulos, anulados, sub judice e última atualização.

Para zerar tudo, apague `database/eleicoes.db` e reinicie — os dados de exemplo voltam.

## API de resultados (link para compartilhar)

```
GET /api/resultados            → resultados do turno atual em JSON
GET /api/resultados?turno=1    → 1º turno
GET /arquivos/exportar         → baixa JSON completo do banco
```

## Estrutura de arquivos

```
eleicoes-roblox-2026/
├── app.py               # aplicação Flask (rotas e cálculos)
├── database.py          # criação do banco + dados iniciais
├── schema.sql           # tabelas do banco
├── requirements.txt     # dependências (flask)
├── iniciar.bat          # atalho para Windows
├── iniciar.sh           # atalho para Linux/Mac
├── database/            # eleicoes.db (criado automaticamente)
├── media/fotos/         # fotos enviadas por upload
├── static/
│   ├── css/style.css    # visual (réplica do painel)
│   ├── js/app.js        # interações (busca, dropdown, preview)
│   └── seed/            # fotos de exemplo
└── templates/           # páginas (Jinja2)
```

## Formato do JSON de importação

```json
{
  "eleicao": "Eleição Geral Ordinária 2026",
  "ano": 2026,
  "turno": "2",
  "cargo": "PRESIDENTE",
  "dados_gerais": {
    "vagas": 1, "secoes": 499248, "totalizadas": 499248,
    "eleitorado": 158745508, "brancos": 1430496, "nulos": 2723305,
    "anulados": 0, "sub_judice": 0,
    "atualizado_em": "25/10/2026 23:26:38"
  },
  "candidatos": [
    { "nome": "LULA", "partido": "PT", "numero": 13,
      "votos": 64256232, "eleito": true,
      "foto_url": "https://exemplo.com/foto.png" }
  ]
}
```

Candidatos já existentes (mesmo nome, eleição e turno) são atualizados; os novos são inseridos.
Se a eleição não existir, ela é criada.

## Observações

- Este site é uma **simulação educacional/diversão** (tema Roblox). Os dados iniciais do
  2º turno reproduzem a tela enviada; os candidatos do 1º turno são fictícios, apenas para
  demonstração.
- O importador por link aceita apenas URLs `http://`/`https://`, com limite de 2 MB e
  timeout de 10 s.
- É um servidor local de desenvolvimento — para publicar na internet, use um servidor WSGI
  (ex.: `waitress-serve --port=80 app:app`).
