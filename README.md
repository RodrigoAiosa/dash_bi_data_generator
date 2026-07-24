# 📊 Painel de Acesso: BI Data Generator

Dashboard em **Python + Streamlit** que lê ao vivo as abas `log_sessoes` e `log_eventos` da planilha de controle de acesso (Google Sheets) e mostra os principais indicadores de uso do [BI Data Generator](https://ai-bidatagenerator.streamlit.app), com filtros na barra lateral.

Os dados vêm diretamente do log de acesso automático do BI Data Generator: cada vez que alguém gera uma base, baixa um ZIP, gera um script SQL etc., um evento é enviado via webhook (Google Apps Script) para a planilha, e este painel lê e visualiza esses eventos em tempo quase real (cache de 5 minutos).

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
├── data.py                       # Leitura (Google Sheets) e transformação dos dados
├── styles.py                     # Paleta, tipografia e helpers de CSS/gráfico (Python)
├── styles.css                    # Folha de estilos (tema "documento/papel", CSS puro)
├── requirements.txt              # streamlit, pandas, plotly
├── .gitignore                    # Ignora .streamlit/secrets.toml e afins
└── .streamlit/
    ├── config.toml               # Tema base do Streamlit (cores combinando com styles.css)
    └── secrets.toml.example      # Modelo do secrets.toml (copie e preencha com seu ID real)
```

**Responsabilidade de cada módulo:**

- `data.py` expõe `carregar_dados()` (cacheada por 5 min, `@st.cache_data(ttl=300)`) e `duracao_para_segundos()`. Não sabe nada de layout/visual.
- `styles.py` expõe `injetar_css()`, `metric_html()`, `fmt_num()` e `base_layout()`. Não sabe nada sobre os dados em si.
- `app.py` só orquestra: chama `data.py` para os dados, `styles.py` para o visual, monta os filtros e desenha os gráficos com Plotly.

---

## 🚀 Como rodar localmente

```bash
git clone https://github.com/RodrigoAiosa/dash_bi_data_generator.git
cd dash_bi_data_generator
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml com o ID real da sua planilha (veja a seção abaixo)
streamlit run app.py
```

O app abre em `http://localhost:8501`.

---

## 📄 Como configurar a planilha de origem

O painel lê os dados de uma planilha Google Sheets com duas abas: `log_sessoes` e `log_eventos` (o mesmo formato gerado automaticamente pelo `log_acesso.py` do BI Data Generator).

### 1. Compartilhamento (passo que mais costuma dar erro 401)

A planilha precisa estar com o **Compartilhamento** geral (não confundir com "Arquivo → Publicar na Web", que é outra configuração) como:

> **Acesso geral: "Qualquer pessoa com o link"** → papel **"Leitor"**

Sem isso, a leitura falha com `HTTP Error 401: Unauthorized`, mesmo que a planilha esteja publicada na web.

### 2. Pegue o ID da planilha

É o trecho entre `/d/` e `/edit` na URL normal da planilha (não o link de "Publicar na Web", que usa um ID diferente):

```
https://docs.google.com/spreadsheets/d/1iyqlaK2mPLDtojqYOUHagTMXlm4-5XT1gZlY26WXor0/edit
                                       ^-------------------- ID --------------------^
```

### 3. Configure o secret

Local (`.streamlit/secrets.toml`) ou no Streamlit Cloud (**Manage app → Settings → Secrets**):

```toml
controle_acesso_sheet_id = "SEU_ID_AQUI"
```

Se não configurar nada, o app cai num ID padrão de exemplo (não recomendado para uso real, configure sempre o seu).

### Como a leitura funciona por baixo dos panos

O app monta, para cada aba, uma URL no formato:

```
https://docs.google.com/spreadsheets/d/{ID}/gviz/tq?tqx=out:csv&sheet={nome_da_aba}
```

Essa é a API `gviz` do Google, que lê **pelo nome da aba** (`log_sessoes`, `log_eventos`) em vez de precisar descobrir o `gid` numérico de cada uma, e devolve os dados prontos como CSV, que o `pandas.read_csv()` já entende direto.

Os dados ficam em cache por 5 minutos (`@st.cache_data(ttl=300)`), para não sobrecarregar o Google Sheets a cada interação. O botão **"🔄 Atualizar agora"** na barra lateral limpa o cache manualmente.

---

## ☁️ Deploy no Streamlit Cloud

1. Suba este repositório (ou aponte para ele diretamente).
2. Ao criar o app, defina o **"Main file path"** como `app.py`.
3. Em **Manage app → Settings → Secrets**, cole:
   ```toml
   controle_acesso_sheet_id = "SEU_ID_AQUI"
   ```
4. Salve, espere ~1 minuto e reinicie o app se necessário ("Reboot app" no menu de três pontinhos).

---

## 🔗 Projeto relacionado

Este painel é o complemento de análise do [**BI Data Generator**](https://github.com/RodrigoAiosa/bi_data_generator), a ferramenta que gera as bases de dados fictícias para 100 setores de negócio diferentes, com medidas DAX, modelo TMDL e scripts SQL automáticos, e que também é a fonte dos dados de uso mostrados aqui (via o módulo `log_acesso.py` daquele projeto).

## ⚖️ Aviso

Todos os dados exibidos aqui são registros de uso reais do BI Data Generator (sessões e ações realizadas), sem nenhuma informação pessoal identificável além do dispositivo, navegador e idioma do acesso. Nenhum dado de conteúdo das bases geradas pelos usuários é coletado ou exibido.
