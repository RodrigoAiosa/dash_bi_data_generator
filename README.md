# Painel de Acesso: BI Data Generator

Dashboard em Python + Streamlit que lê ao vivo as abas `log_sessoes` e
`log_eventos` da planilha de controle de acesso, com os principais
indicadores de uso e filtros de Ano, Mês, Setor, Ação, Status e Dispositivo.

## Estrutura do projeto

```
dashboard_acesso/
├── app.py                        # Entry point: layout, filtros, KPIs, gráficos
├── data.py                       # Leitura e transformação dos dados da planilha
├── styles.py                     # Paleta, tipografia e helpers de CSS/gráfico
├── styles.css                    # Folha de estilos (tema "documento/papel")
├── requirements.txt
├── .gitignore
└── .streamlit/
    ├── config.toml               # Tema base do Streamlit
    └── secrets.toml.example      # Modelo do secrets.toml (copie e preencha)
```

## Como rodar localmente

```
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml com o ID real da sua planilha
streamlit run app.py
```

## Como configurar a planilha

1. A planilha precisa estar com o compartilhamento **"Qualquer pessoa com o link pode visualizar"** (ou publicada na web, como você já fez).
2. Pegue o ID da planilha: é o trecho entre `/d/` e `/edit` na URL normal dela, por exemplo:
   ```
   https://docs.google.com/spreadsheets/d/1iyqlaK2mPLDtojqYOUHagTMXlm4-5XT1gZlY26WXor0/edit
                                          ^-------------------- ID --------------------^
   ```
3. Crie `.streamlit/secrets.toml` (local) ou configure em **Manage app → Settings → Secrets** (Streamlit Cloud):
   ```toml
   controle_acesso_sheet_id = "1iyqlaK2mPLDtojqYOUHagTMXlm4-5XT1gZlY26WXor0"
   ```
4. Se não configurar nada, o app usa por padrão o ID que já apareceu nas suas telas anteriores, mas o ideal é sempre configurar explicitamente.

O app lê os dados via `https://docs.google.com/spreadsheets/d/{ID}/gviz/tq?tqx=out:csv&sheet={nome_da_aba}`, que funciona pelo **nome da aba** (não precisa descobrir o `gid` numérico de cada uma). Os dados ficam em cache por 5 minutos (há um botão "🔄 Atualizar agora" na barra lateral para forçar).

## Deploy no Streamlit Cloud

Suba esta pasta (`dashboard_acesso/`) como um repositório (ou subpasta de repositório) próprio, e aponte o "Main file path" para `app.py` ao criar o app no Streamlit Cloud.
