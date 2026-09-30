# 📊 Painel de Acesso: BI Data Generator

Dashboard em **Python + Streamlit** que lê ao vivo a tabela `logs_uso` do banco Supabase (PostgreSQL) e mostra os principais indicadores de uso do [BI Data Generator](https://ai-bidatagenerator.streamlit.app), com filtros na barra lateral.

Os dados vêm diretamente do log de acesso automático do BI Data Generator: cada vez que alguém gera uma base, baixa um ZIP, gera um script SQL etc., um evento é gravado no Supabase, e este painel lê e visualiza esses eventos em tempo quase real.

---

## ✨ O que o painel mostra

### KPIs (topo da tela)

| KPI | O que significa |
|---|---|
| **Sessões** | Número de acessos únicos (`id_sessao` distintos) no período filtrado |
| **Bases geradas** | Quantas vezes a ação `gerou_base` aconteceu, + total de linhas geradas somadas |
| **Taxa de sucesso** | % dos eventos com `status = sucesso` (o resto é erro, ex.: falha ao gerar/exportar) |
| **Duração média** | Tempo médio de sessão, calculado a partir de `inicio_acesso`/`fim_acesso` |
| **Setor mais gerado** | Setor que mais aparece nas ações `gerou_base` do período filtrado |

### Gráficos

- **Evolução de uso ao longo do tempo**: área com o total de eventos por dia
- **Top 10 setores mais gerados**: barras horizontais, dos 100 setores do BI Data Generator
- **Ações realizadas**: rosca com a proporção de `gerou_base`, `gerou_sql`, `baixou_zip`, `baixou_dicionario`, `baixou_sql`
- **Sessões por dispositivo**: barras (desktop vs. mobile)
- **Uso dos modos especiais**: % das bases geradas com Modo Anomalias e/ou Deriva Temporal ativos

### Tabela

- **Eventos recentes**: os últimos 100 eventos, com data/hora, ação, setor, volume de linhas, status e detalhe do erro (quando houver)

### Filtros (barra lateral)

Todos em formato de **combobox** (`st.selectbox`, um valor por vez, com opção **"Todos"**):

- **Ano** e **Mês** (o Mês só mostra os meses que existem dentro do Ano escolhido)
- **Setor**
- **Ação** (`gerou_base`, `gerou_sql`, `baixou_zip`, `baixou_dicionario`, `baixou_sql`)
- **Status** (`sucesso` / `erro`)
- **Dispositivo** (`desktop` / `mobile`)

Abaixo dos filtros: aviso de atualização automática a cada 5 minutos, a **data e hora exata da última atualização** (fuso de Brasília), e o botão **"🔄 Atualizar agora"** (centralizado), que limpa o cache e busca os dados de novo na hora.

---

## 🎨 Identidade visual

Mesmo estilo "documento/papel" usado no BI Data Generator: fundo claro, cabeçalho azul-marinho com selo "✓ ao vivo", tipografia serifada **Bitter** para títulos/KPIs e monoespaçada **IBM Plex Mono** para rótulos/eixos, paleta ink/verde/rust/dourado. Os rótulos de eixo e legenda dos gráficos são forçados em preto puro para máxima legibilidade contra o fundo claro. Os cards de KPI têm altura e largura padronizadas entre si.

---

## 🗂 Estrutura do projeto

```
dash_bi_data_generator/
├── app.py                        # Entry point: layout, filtros, KPIs, gráficos, tabela
├── data.py                       # Leitura (Supabase/PostgreSQL) e transformação dos dados
├── styles.py                     # Paleta, tipografia e helpers de CSS/gráfico (Python)
├── styles.css                    # Folha de estilos (tema "documento/papel", CSS puro)
├── requirements.txt              # streamlit, pandas, plotly, psycopg
├── .gitignore                    # Ignora .streamlit/secrets.toml e afins
└── .streamlit/
    ├── config.toml               # Tema base do Streamlit (cores combinando com styles.css)
    └── secrets.toml.example      # Modelo do secrets.toml (copie e preencha com seu ID real)
```

**Responsabilidade de cada módulo:**

- `data.py` expõe `carregar_dados()` (cacheada por 15 min, `@st.cache_data(ttl=900)`) e `duracao_para_segundos()`. Não sabe nada de layout/visual.
- `styles.py` expõe `injetar_css()`, `metric_html()`, `fmt_num()` e `base_layout()`. Não sabe nada sobre os dados em si.
- `app.py` só orquestra: chama `data.py` para os dados, `styles.py` para o visual, monta os filtros e desenha os gráficos com Plotly.

---

## 🚀 Como rodar localmente

```bash
git clone https://github.com/RodrigoAiosa/dash_bi_data_generator.git
cd dash_bi_data_generator
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml com os dados de conexão do Supabase (veja a seção abaixo)
streamlit run app.py
```

O app abre em `http://localhost:8501`.

---

## 🗄 Fonte de dados: Supabase

O painel lê a tabela `public.logs_uso` do projeto Supabase **BD_BIDATAGENERATOR**, onde o BI Data Generator grava cada acesso e cada ação. A tabela tem dois tipos de linha (coluna `tipo_evento`):

| tipo_evento | Vira no painel | Colunas usadas |
|---|---|---|
| `sessao_inicio` | **sessões** | `id_sessao`, `data_hora_evento`, `dispositivo`, `navegador`, `idioma_interface` |
| `clique` | **eventos** | `acao`, `setor_gerado`, `volume_linhas`, `status`, `erro_detalhe`, `anomalia_ativada`, `deriva_temporal_ativada` |

A duração de cada sessão é o maior `duracao_segundos` entre os cliques dela (esse campo guarda o tempo desde o início da sessão). A tabela `registros` (dados de cadastro) **não** é lida pelo painel.

### Usuário somente leitura

A conexão usa o usuário `dash_leitura`, que só consegue fazer `SELECT` em `logs_uso` (tem uma policy de RLS própria para isso), não enxerga `registros` e não pode gravar nada. Não use o usuário `postgres` no painel.

### Configure o secret

Local (`.streamlit/secrets.toml`) ou no Streamlit Cloud (**Manage app → Settings → Secrets**), com os dados do **Session pooler** (botão **Connect** no topo do Supabase):

```toml
[supabase]
host = "aws-0-us-west-2.pooler.supabase.com"
port = 5432
dbname = "postgres"
user = "dash_leitura.SEU_PROJECT_REF"
password = "SENHA_DO_USUARIO_DE_LEITURA"
```

A conexão usa SSL (`sslmode = "require"`). Os dados ficam em cache por 15 minutos (`@st.cache_data(ttl=900)`), e o botão **"🔄 Atualizar agora"** na barra lateral limpa o cache manualmente.

---

## ☁️ Deploy no Streamlit Cloud

1. Suba este repositório (ou aponte para ele diretamente).
2. Ao criar o app, defina o **"Main file path"** como `app.py`.
3. Em **Manage app → Settings → Secrets**, cole o bloco `[supabase]` acima com os valores reais.
4. Salve, espere ~1 minuto e reinicie o app se necessário ("Reboot app" no menu de três pontinhos).

---

## 🔗 Projeto relacionado

Este painel é o complemento de análise do [**BI Data Generator**](https://github.com/RodrigoAiosa/bi_data_generator), a ferramenta que gera as bases de dados fictícias para 100 setores de negócio diferentes, com medidas DAX, modelo TMDL e scripts SQL automáticos, e que também é a fonte dos dados de uso mostrados aqui (via o módulo `log_acesso.py` daquele projeto).

## ⚖️ Aviso

Todos os dados exibidos aqui são registros de uso reais do BI Data Generator (sessões e ações realizadas), sem nenhuma informação pessoal identificável além do dispositivo, navegador e idioma do acesso. Nenhum dado de conteúdo das bases geradas pelos usuários é coletado ou exibido.
