"""
app.py: Painel de Acesso do BI Data Generator.

Le as abas log_sessoes e log_eventos direto da planilha do Google Sheets
(publicada na web) e mostra os principais indicadores de uso, com filtros
de Ano, Mes, Setor, Acao, Status e Dispositivo na barra lateral.

Como configurar: veja o README.md deste projeto.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from data import carregar_dados, duracao_para_segundos
from styles import (
    ACOES_LABEL, GREEN, INK, MESES_PT, PALETTE, RUST,
    base_layout, fmt_num, injetar_css, metric_html,
)

st.set_page_config(
    page_title="Painel de Acesso: BI Data Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    injetar_css()

    st.markdown("""
    <div class="dash-header">
        <div class="dash-stamp">&#10003; ao vivo</div>
        <p class="dash-eyebrow">Relatório de Uso · Dados em Tempo Real</p>
        <h1 class="dash-title">Painel de Acesso: BI Data Generator</h1>
        <p class="dash-meta">Fonte: planilha controle_acesso (Google Sheets) · Atualiza a cada 5 minutos</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        sessoes, eventos, quando_carregou = carregar_dados()
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
    st.sidebar.markdown(
        f'<p class="ultima-atualizacao">🕒 Última atualização:<br>{quando_carregou.strftime("%d/%m/%Y %H:%M:%S")}</p>',
        unsafe_allow_html=True,
    )
    _col_esq, _col_meio, _col_dir = st.sidebar.columns([1, 3, 1])
    with _col_meio:
        if st.button("🔄 Atualizar agora", use_container_width=True):
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

    duracoes = ses["duracao"].dropna().map(duracao_para_segundos).dropna() if "duracao" in ses.columns else pd.Series(dtype=float)
    duracao_media_seg = duracoes.mean() if len(duracoes) else 0
    duracao_media_fmt = f"{int(duracao_media_seg // 60)}min {int(duracao_media_seg % 60)}s" if duracao_media_seg else "-"

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(metric_html("Sessões", fmt_num(total_sessoes), "acessos únicos"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_html("Bases geradas", fmt_num(total_bases), f"{fmt_num(total_linhas)} linhas no total"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_html("Taxa de sucesso", f"{fmt_num(taxa_sucesso, 1)}%", f"{total_eventos} eventos"), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_html("Duração média", duracao_media_fmt, "por sessão"), unsafe_allow_html=True)
    with col5:
        st.markdown(metric_html("Setor mais gerado", str(setor_top)[:18], ""), unsafe_allow_html=True)

    # ── Gráfico: evolução diária de eventos ─────────────────────────────────
    st.markdown('<h3 class="section-title">Evolução de uso ao longo do tempo</h3>', unsafe_allow_html=True)
    por_dia = ev.groupby("dia").size().reset_index(name="eventos")
    fig_evolucao = px.area(por_dia, x="dia", y="eventos", labels={"dia": "", "eventos": "Eventos"})
    fig_evolucao.update_traces(line_color=INK, fillcolor="rgba(22,35,63,0.08)")
    base_layout(fig_evolucao, "Eventos por dia")
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
            fig_setores.update_traces(marker_color=INK)
            base_layout(fig_setores, "Top 10 setores mais gerados")
            st.plotly_chart(fig_setores, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhuma base gerada (ação 'gerou_base') para os filtros selecionados.")

    with col_b:
        contagem_acoes = ev["acao"].map(lambda a: ACOES_LABEL.get(a, a)).value_counts()
        if not contagem_acoes.empty:
            fig_acoes = px.pie(values=contagem_acoes.values, names=contagem_acoes.index, hole=0.55)
            fig_acoes.update_traces(marker=dict(colors=PALETTE))
            base_layout(fig_acoes, "Ações realizadas")
            st.plotly_chart(fig_acoes, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhuma ação para os filtros selecionados.")

    # ── Gráficos: dispositivo + anomalia/drift ──────────────────────────────
    col_c, col_d = st.columns(2)
    with col_c:
        contagem_disp = ses["dispositivo"].value_counts() if "dispositivo" in ses.columns else pd.Series(dtype=int)
        if not contagem_disp.empty:
            fig_disp = px.bar(x=contagem_disp.index, y=contagem_disp.values, labels={"x": "", "y": "Sessões"})
            fig_disp.update_traces(marker_color=GREEN)
            base_layout(fig_disp, "Sessões por dispositivo")
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
        fig_modos.update_traces(marker_color=RUST)
        base_layout(fig_modos, "Uso dos modos especiais")
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
