"""
app.py: Dashboard de Acesso do BI Data Generator.

Le as abas log_sessoes e log_eventos direto da planilha do Google Sheets
(publicada na web) e mostra os principais indicadores de uso, com filtros
de Ano, Mes, Setor, Acao, Status e Dispositivo na barra lateral.

Como configurar:
    Defina o ID da planilha em .streamlit/secrets.toml:
        controle_acesso_sheet_id = "SEU_ID_AQUI"
    (o ID e o trecho entre /d/ e /edit na URL da planilha, ex.:
     https://docs.google.com/spreadsheets/d/ESSE_ID_AQUI/edit)

A planilha precisa estar com o compartilhamento "Qualquer pessoa com o
link pode visualizar" (ou publicada na web), senao a leitura falha.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Painel de Acesso: BI Data Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paleta e tipografia (mesmo estilo "documento/papel" do gerador) ──────────
_PAPER_BODY = "#EEF0EA"
_PAPER      = "#F8F9F4"
_GRID       = "#D8DAD0"
_TEXT       = "#6B6F66"
_INK        = "#16233F"
_GREEN      = "#1F6F54"
_RUST       = "#A63D2F"
_GOLD       = "#B8862E"
_PALETTE    = [_INK, _GREEN, _RUST, _GOLD, "#223058", "#6E86A8", "#8A7F5E"]
_FONT_DISPLAY = "Bitter, serif"
_FONT_MONO    = "IBM Plex Mono, monospace"
_FONT_BODY    = "Inter, sans-serif"

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

ACOES_LABEL = {
    "gerou_base": "Gerou base",
    "gerou_sql": "Gerou SQL",
    "baixou_zip": "Baixou ZIP",
    "baixou_dicionario": "Baixou dicionário",
    "baixou_sql": "Baixou SQL",
}


def _injetar_css() -> None:
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bitter:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background: {_PAPER_BODY} !important;
    }}
    html, body, [class*="css"] {{ font-family: {_FONT_BODY} !important; }}

    [data-testid="stSidebar"] {{
        background: {_PAPER} !important;
        border-right: 1px solid {_GRID} !important;
    }}
    [data-testid="stSidebar"] * {{ color: {_TEXT} !important; }}
    [data-testid="stSidebar"] label p {{
        font-family: {_FONT_MONO} !important;
        font-size: 11px !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        color: {_INK} !important;
    }}

    .dash-header {{
        background: {_INK}; color: {_PAPER_BODY};
        padding: 1.6rem 2rem 1.8rem; border-radius: 10px;
        position: relative; overflow: hidden; margin-bottom: 1.2rem;
    }}
    .dash-eyebrow {{
        font-family: {_FONT_MONO}; font-size: 11px; letter-spacing: 0.14em;
        text-transform: uppercase; color: #9FB0C9; margin: 0 0 0.3rem;
    }}
    .dash-title {{
        font-family: {_FONT_DISPLAY}; font-weight: 800; font-size: 1.7rem;
        margin: 0; color: {_PAPER_BODY}; letter-spacing: -0.01em;
    }}
    .dash-meta {{
        font-family: {_FONT_MONO}; font-size: 12px; color: #B9C4D8; margin: 0.4rem 0 0;
    }}
    .dash-stamp {{
        position: absolute; top: 1.3rem; right: 1.8rem;
        border: 2px solid #6E86A8; border-radius: 6px; color: #9FB0C9;
        font-family: {_FONT_MONO}; font-size: 10px; letter-spacing: 0.1em;
        text-transform: uppercase; padding: 4px 10px; transform: rotate(-5deg); opacity: 0.85;
    }}

    .kpi-stamp {{
        background: {_PAPER}; border: 2px double {_INK}; border-radius: 4px;
        padding: 0.9rem 1rem 0.8rem; height: 100%;
    }}
    .kpi-label {{
        font-family: {_FONT_MONO}; font-size: 10px; letter-spacing: 0.08em;
        text-transform: uppercase; color: {_TEXT}; margin: 0 0 0.4rem;
    }}
    .kpi-value {{
        font-family: {_FONT_DISPLAY}; font-weight: 700; font-size: 1.4rem;
        margin: 0; color: {_INK}; line-height: 1.15;
    }}
    .kpi-sub {{
        font-family: {_FONT_MONO}; font-size: 10px; color: {_TEXT}; margin: 0.3rem 0 0;
    }}

    h3.section-title {{
        font-family: {_FONT_DISPLAY}; font-weight: 800; color: {_INK};
        font-size: 1.15rem; margin: 1.6rem 0 0.8rem;
        border-bottom: 1px solid {_GRID}; padding-bottom: 0.5rem;
    }}
    [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {{
        background: {_PAPER}; border: 1px solid {_GRID}; border-radius: 8px;
        padding: 0.6rem;
    }}
    </style>
    """, unsafe_allow_html=True)


def _metric_html(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<p class="kpi-sub">{sub}</p>' if sub else ""
    return f'<div class="kpi-stamp"><p class="kpi-label">{label}</p><p class="kpi-value">{value}</p>{sub_html}</div>'


def _fmt_num(v, casas=0) -> str:
    s = f"{v:,.{casas}f}"
    return s.translate(str.maketrans({",": "\x00", ".": ","})).replace("\x00", ".")


def _base_layout(fig, titulo: str = ""):
    fig.update_layout(
        paper_bgcolor=_PAPER, plot_bgcolor=_PAPER,
        font=dict(family=_FONT_BODY, color=_TEXT, size=12),
        title=dict(text=titulo, font=dict(color=_INK, size=14, family=_FONT_DISPLAY), x=0.01),
        margin=dict(l=10, r=10, t=40 if titulo else 10, b=10),
        colorway=_PALETTE,
        separators=",.",
        legend=dict(font=dict(family=_FONT_MONO, size=11)),
    )
    fig.update_xaxes(gridcolor=_GRID, zeroline=False, tickfont=dict(family=_FONT_MONO, size=10))
    fig.update_yaxes(gridcolor=_GRID, zeroline=False, tickfont=dict(family=_FONT_MONO, size=10))
    return fig


# ── Carregamento de dados ────────────────────────────────────────────────────

def _sheet_id() -> str:
    return st.secrets.get("controle_acesso_sheet_id", "1iyqlaK2mPLDtojqYOUHagTMXlm4-5XT1gZlY26WXor0")


def _url_aba(nome_aba: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{_sheet_id()}/gviz/tq?tqx=out:csv&sheet={nome_aba}"


@st.cache_data(ttl=300, show_spinner="Carregando dados da planilha...")
def carregar_dados():
    sessoes = pd.read_csv(_url_aba("log_sessoes"))
    eventos = pd.read_csv(_url_aba("log_eventos"))

    sessoes["data_hora"] = pd.to_datetime(sessoes["data_hora"], errors="coerce")
    eventos["data_hora_evento"] = pd.to_datetime(eventos["data_hora_evento"], errors="coerce")

    eventos["ano"] = eventos["data_hora_evento"].dt.year
    eventos["mes"] = eventos["data_hora_evento"].dt.month
    eventos["dia"] = eventos["data_hora_evento"].dt.date

    return sessoes, eventos


def _duracao_para_segundos(duracao_str: str):
    try:
        h, m, s = str(duracao_str).split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return None


# ── App ───────────────────────────────────────────────────────────────────────

def main():
    _injetar_css()

    st.markdown("""
    <div class="dash-header">
        <div class="dash-stamp">&#10003; ao vivo</div>
        <p class="dash-eyebrow">Relatório de Uso · Dados em Tempo Real</p>
        <h1 class="dash-title">Painel de Acesso: BI Data Generator</h1>
        <p class="dash-meta">Fonte: planilha controle_acesso (Google Sheets) · Atualiza a cada 5 minutos</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        sessoes, eventos = carregar_dados()
    except Exception as e:
        st.error(f"Não foi possível carregar a planilha. Verifique o compartilhamento e o ID configurado. Detalhe: {e}")
        st.stop()

    if eventos.empty:
        st.info("Ainda não há eventos registrados na planilha.")
        st.stop()

    # ── Filtros (sidebar) ────────────────────────────────────────────────────
    st.sidebar.markdown("### 🔎 Filtros")

    anos_disponiveis = sorted(eventos["ano"].dropna().unique().astype(int).tolist())
    anos_sel = st.sidebar.multiselect("Ano", anos_disponiveis, default=anos_disponiveis)

    eventos_ano = eventos[eventos["ano"].isin(anos_sel)] if anos_sel else eventos.iloc[0:0]
    meses_disponiveis = sorted(eventos_ano["mes"].dropna().unique().astype(int).tolist())
    meses_sel = st.sidebar.multiselect(
        "Mês", meses_disponiveis, default=meses_disponiveis,
        format_func=lambda m: MESES_PT.get(m, str(m)),
    )

    setores_disponiveis = sorted(eventos["setor_gerado"].dropna().unique().tolist())
    setores_sel = st.sidebar.multiselect("Setor", setores_disponiveis, default=setores_disponiveis)

    acoes_disponiveis = sorted(eventos["acao"].dropna().unique().tolist())
    acoes_sel = st.sidebar.multiselect(
        "Ação", acoes_disponiveis, default=acoes_disponiveis,
        format_func=lambda a: ACOES_LABEL.get(a, a),
    )

    status_disponiveis = sorted(eventos["status"].dropna().unique().tolist())
    status_sel = st.sidebar.multiselect("Status", status_disponiveis, default=status_disponiveis)

    dispositivos_disponiveis = sorted(sessoes["dispositivo"].dropna().unique().tolist()) if "dispositivo" in sessoes else []
    dispositivos_sel = st.sidebar.multiselect("Dispositivo", dispositivos_disponiveis, default=dispositivos_disponiveis)

    st.sidebar.caption("Os dados vêm direto da planilha e atualizam automaticamente a cada 5 minutos.")
    if st.sidebar.button("🔄 Atualizar agora"):
        st.cache_data.clear()
        st.rerun()

    # ── Aplica filtros ───────────────────────────────────────────────────────
    ev = eventos[
        eventos["ano"].isin(anos_sel)
        & eventos["mes"].isin(meses_sel)
        & (eventos["setor_gerado"].isin(setores_sel) | eventos["setor_gerado"].isna())
        & eventos["acao"].isin(acoes_sel)
        & eventos["status"].isin(status_sel)
    ]

    ses = sessoes.copy()
    if dispositivos_sel and "dispositivo" in ses.columns:
        ses = ses[ses["dispositivo"].isin(dispositivos_sel)]
    if anos_sel:
        ses = ses[ses["data_hora"].dt.year.isin(anos_sel)]

    if ev.empty:
        st.warning("Nenhum evento encontrado para os filtros selecionados.")
        st.stop()

    # ── KPIs ─────────────────────────────────────────────────────────────────
    total_sessoes = ses["id_sessao"].nunique() if "id_sessao" in ses.columns else 0
    total_eventos = len(ev)
    gerou_base = ev[ev["acao"] == "gerou_base"]
    total_bases = len(gerou_base)
    total_linhas = gerou_base["volume_linhas"].fillna(0).sum()
    taxa_sucesso = (ev["status"] == "sucesso").mean() * 100 if total_eventos else 0
    setor_top = gerou_base["setor_gerado"].mode().iloc[0] if not gerou_base.empty and not gerou_base["setor_gerado"].mode().empty else "-"

    duracoes = ses["duracao"].dropna().map(_duracao_para_segundos).dropna() if "duracao" in ses.columns else pd.Series(dtype=float)
    duracao_media_seg = duracoes.mean() if len(duracoes) else 0
    duracao_media_fmt = f"{int(duracao_media_seg // 60)}min {int(duracao_media_seg % 60)}s" if duracao_media_seg else "-"

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(_metric_html("Sessões", _fmt_num(total_sessoes), "acessos únicos"), unsafe_allow_html=True)
    with col2:
        st.markdown(_metric_html("Bases geradas", _fmt_num(total_bases), f"{_fmt_num(total_linhas)} linhas no total"), unsafe_allow_html=True)
    with col3:
        st.markdown(_metric_html("Taxa de sucesso", f"{_fmt_num(taxa_sucesso, 1)}%", f"{total_eventos} eventos"), unsafe_allow_html=True)
    with col4:
        st.markdown(_metric_html("Duração média", duracao_media_fmt, "por sessão"), unsafe_allow_html=True)
    with col5:
        st.markdown(_metric_html("Setor mais gerado", str(setor_top)[:18], ""), unsafe_allow_html=True)

    # ── Gráfico: evolução diária de eventos ─────────────────────────────────
    st.markdown('<h3 class="section-title">Evolução de uso ao longo do tempo</h3>', unsafe_allow_html=True)
    por_dia = ev.groupby("dia").size().reset_index(name="eventos")
    fig_evolucao = px.area(por_dia, x="dia", y="eventos", labels={"dia": "", "eventos": "Eventos"})
    fig_evolucao.update_traces(line_color=_INK, fillcolor="rgba(22,35,63,0.08)")
    _base_layout(fig_evolucao, "Eventos por dia")
    st.plotly_chart(fig_evolucao, use_container_width=True, config={"displayModeBar": False})

    # ── Gráficos: setores + ações ────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        top_setores = gerou_base["setor_gerado"].value_counts().head(10).sort_values()
        if not top_setores.empty:
            fig_setores = px.bar(
                x=top_setores.values, y=top_setores.index, orientation="h",
                labels={"x": "Bases geradas", "y": ""},
            )
            fig_setores.update_traces(marker_color=_INK)
            _base_layout(fig_setores, "Top 10 setores mais gerados")
            st.plotly_chart(fig_setores, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhuma base gerada (ação 'gerou_base') para os filtros selecionados.")

    with col_b:
        contagem_acoes = ev["acao"].map(lambda a: ACOES_LABEL.get(a, a)).value_counts()
        if not contagem_acoes.empty:
            fig_acoes = px.pie(
                values=contagem_acoes.values, names=contagem_acoes.index, hole=0.55,
            )
            fig_acoes.update_traces(marker=dict(colors=_PALETTE))
            _base_layout(fig_acoes, "Ações realizadas")
            st.plotly_chart(fig_acoes, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhuma ação para os filtros selecionados.")

    # ── Gráficos: dispositivo/navegador + anomalia/drift ────────────────────
    col_c, col_d = st.columns(2)
    with col_c:
        contagem_disp = ses["dispositivo"].value_counts() if "dispositivo" in ses.columns else pd.Series(dtype=int)
        if not contagem_disp.empty:
            fig_disp = px.bar(x=contagem_disp.index, y=contagem_disp.values, labels={"x": "", "y": "Sessões"})
            fig_disp.update_traces(marker_color=_GREEN)
            _base_layout(fig_disp, "Sessões por dispositivo")
            st.plotly_chart(fig_disp, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Sem dados de dispositivo para o período selecionado.")

    with col_d:
        anomalia_pct = (gerou_base["anomalia_ativada"] == "sim").mean() * 100 if not gerou_base.empty else 0
        drift_pct = (gerou_base["deriva_temporal_ativada"] == "sim").mean() * 100 if not gerou_base.empty else 0
        fig_modos = px.bar(
            x=["Anomalias", "Deriva Temporal"], y=[anomalia_pct, drift_pct],
            labels={"x": "", "y": "% das bases geradas"},
        )
        fig_modos.update_traces(marker_color=_RUST)
        _base_layout(fig_modos, "Uso dos modos especiais")
        st.plotly_chart(fig_modos, use_container_width=True, config={"displayModeBar": False})

    # ── Tabela: eventos recentes ─────────────────────────────────────────────
    st.markdown('<h3 class="section-title">Eventos recentes</h3>', unsafe_allow_html=True)
    colunas_tabela = ["data_hora_evento", "acao", "setor_gerado", "volume_linhas", "status", "erro_detalhe"]
    colunas_existentes = [c for c in colunas_tabela if c in ev.columns]
    st.dataframe(
        ev[colunas_existentes].sort_values("data_hora_evento", ascending=False).head(100),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
