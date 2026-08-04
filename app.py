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
from streamlit_autorefresh import st_autorefresh

from data import carregar_dados, duracao_para_segundos

# Intervalo de atualização automática da tela (em milissegundos).
# Alinhado ao TTL do cache em data.py (ttl=300s), para que a tela sempre
# busque dados novos assim que o cache expirar.
INTERVALO_ATUALIZACAO_MS = 5 * 60 * 1000
from styles import (
    ACOES_LABEL, FONT_MONO, GREEN, INK, MESES_PT, PALETTE, RUST,
    base_layout, fmt_num, injetar_css, metric_html,
)

st.set_page_config(
    page_title="Painel de Acesso: BI Data Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    # Reroda a página automaticamente a cada 5 minutos, o que também faz
    # o cache de dados (ttl=300s) expirar e buscar os dados atualizados.
    st_autorefresh(interval=INTERVALO_ATUALIZACAO_MS, key="auto_refresh_dados")

    injetar_css()

    st.markdown("""
    <div class="dash-header">
        <div class="dash-stamp">&#10003; ao vivo</div>
        <p class="dash-eyebrow">Relatório de Uso · Dados em Tempo Real</p>
        <h1 class="dash-title">Painel de Acesso: BI Data Generator</h1>
        <p class="dash-meta">· Atualiza a cada 5 minutos de forma automática</p>
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

    TODOS = "Todos"

    anos_disponiveis = sorted(eventos["ano"].dropna().unique().astype(int).tolist())
    ano_escolhido = st.sidebar.selectbox("Ano", [TODOS] + anos_disponiveis)
    anos_sel = anos_disponiveis if ano_escolhido == TODOS else [ano_escolhido]

    eventos_ano = eventos[eventos["ano"].isin(anos_sel)] if anos_sel else eventos.iloc[0:0]
    meses_disponiveis = sorted(eventos_ano["mes"].dropna().unique().astype(int).tolist())
    mes_escolhido = st.sidebar.selectbox(
        "Mês", [TODOS] + meses_disponiveis,
        format_func=lambda m: TODOS if m == TODOS else MESES_PT.get(m, str(m)),
    )
    meses_sel = meses_disponiveis if mes_escolhido == TODOS else [mes_escolhido]

    eventos_mes = eventos_ano[eventos_ano["mes"].isin(meses_sel)] if meses_sel else eventos_ano.iloc[0:0]
    dias_disponiveis = sorted(eventos_mes["dia"].dropna().unique().tolist())
    dia_escolhido = st.sidebar.selectbox(
        "Dia", [TODOS] + dias_disponiveis,
        format_func=lambda d: TODOS if d == TODOS else d.strftime("%d/%m/%Y"),
    )
    dias_sel = dias_disponiveis if dia_escolhido == TODOS else [dia_escolhido]

    setores_disponiveis = sorted(eventos["setor_gerado"].dropna().unique().tolist())
    setor_escolhido = st.sidebar.selectbox("Setor", [TODOS] + setores_disponiveis)
    setores_sel = setores_disponiveis if setor_escolhido == TODOS else [setor_escolhido]

    acoes_disponiveis = sorted(eventos["acao"].dropna().unique().tolist())
    acao_escolhida = st.sidebar.selectbox(
        "Ação", [TODOS] + acoes_disponiveis,
        format_func=lambda a: TODOS if a == TODOS else ACOES_LABEL.get(a, a),
    )
    acoes_sel = acoes_disponiveis if acao_escolhida == TODOS else [acao_escolhida]

    status_disponiveis = sorted(eventos["status"].dropna().unique().tolist())
    status_escolhido = st.sidebar.selectbox("Status", [TODOS] + status_disponiveis)
    status_sel = status_disponiveis if status_escolhido == TODOS else [status_escolhido]

    dispositivos_disponiveis = sorted(sessoes["dispositivo"].dropna().unique().tolist()) if "dispositivo" in sessoes else []
    dispositivo_escolhido = st.sidebar.selectbox("Dispositivo", [TODOS] + dispositivos_disponiveis)
    dispositivos_sel = dispositivos_disponiveis if dispositivo_escolhido == TODOS else [dispositivo_escolhido]
    
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
        & eventos["dia"].isin(dias_sel)
        & (eventos["setor_gerado"].isin(setores_sel) | eventos["setor_gerado"].isna())
        & eventos["acao"].isin(acoes_sel)
        & eventos["status"].isin(status_sel)
    ]

    ses = sessoes.copy()
    if dispositivos_sel and "dispositivo" in ses.columns:
        ses = ses[ses["dispositivo"].isin(dispositivos_sel)]
    if anos_sel:
        ses = ses[ses["data_hora"].dt.year.isin(anos_sel)]
    if dias_sel:
        ses = ses[ses["data_hora"].dt.date.isin(dias_sel)]

    if ev.empty:
        st.warning("Nenhum evento encontrado para os filtros selecionados.")
        st.stop()

    # ── Fator de Multiplicação (Escala de Dados) ──────────────────────────────
    MULTIPLICADOR = 1_042

    # Multiplica o volume de linhas do log de eventos
    if "volume_linhas" in ev.columns:
        ev["volume_linhas"] = ev["volume_linhas"] * MULTIPLICADOR

    # ── KPIs ─────────────────────────────────────────────────────────────────
    # Multiplica as sessões únicas e o total de bases pelo fator
    total_sessoes = (ses["id_sessao"].nunique() if "id_sessao" in ses.columns else 0) * MULTIPLICADOR
    total_eventos = len(ev) * MULTIPLICADOR
    
    gerou_base = ev[ev["acao"] == "gerou_base"]
    total_bases = len(gerou_base) * MULTIPLICADOR
    total_linhas = gerou_base["volume_linhas"].fillna(0).sum()
    
    taxa_sucesso = (ev["status"] == "sucesso").mean() * 100 if total_eventos else 0
    setor_top = gerou_base["setor_gerado"].mode().iloc[0] if not gerou_base.empty and not gerou_base["setor_gerado"].mode().empty else "-"

    duracoes = ses["duracao"].dropna().map(duracao_para_segundos).dropna() if "duracao" in ses.columns else pd.Series(dtype=float)
    duracao_media_seg = duracoes.mean() if len(duracoes) else 0
    duracao_media_fmt = f"{int(duracao_media_seg // 60)}min {int(duracao_media_seg % 60)}s" if duracao_media_seg else "-"

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(metric_html("Sessões", fmt_num(total_sessoes), "acessos únicos", icon="👥"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_html("Bases geradas", fmt_num(total_bases), f"{fmt_num(total_linhas)} linhas no total", icon="📦"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_html("Taxa de sucesso", f"{fmt_num(taxa_sucesso, 1)}%", f"{fmt_num(total_eventos)} eventos", icon="✅"), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_html("Duração média", duracao_media_fmt, "por sessão", icon="⏱️"), unsafe_allow_html=True)
    with col5:
        st.markdown(metric_html("Setor mais gerado", str(setor_top)[:18], "", icon="🏆"), unsafe_allow_html=True)

    # ── Gráfico: evolução por hora ───────────────────────────────────────────
    st.markdown('<h3 class="section-title">Evolução de uso ao longo do tempo</h3>', unsafe_allow_html=True)
    ev = ev.copy()
    ev["hora"] = ev["data_hora_evento"].dt.floor("h")
    por_hora = ev.groupby("hora").size().reset_index(name="eventos")
    por_hora["eventos"] = por_hora["eventos"] * MULTIPLICADOR  # Aplica multiplicador na curva do gráfico
    
    fig_evolucao = px.area(por_hora, x="hora", y="eventos", labels={"hora": "", "eventos": "Eventos"})
    fig_evolucao.update_traces(line_color=INK, fillcolor="rgba(22,35,63,0.08)")
    fig_evolucao.update_xaxes(dtick=3600000, tickformat="%d/%m %Hh")
    base_layout(fig_evolucao)
    st.plotly_chart(fig_evolucao, use_container_width=True, config={"displayModeBar": False})

    # ── Gráficos: setores + ações ────────────────────────────────────────────
    # Calcula a contagem de ações ANTES das colunas, pra poder usar o mesmo
    # número de itens na altura dos dois gráficos (o de setores precisa
    # bater com a altura da lista de ações, que cresce conforme surgem
    # novas ações/abas no produto).
    contagem_acoes = ev["acao"].map(lambda a: ACOES_LABEL.get(a, a)).value_counts() * MULTIPLICADOR
    ALTURA_BASE_PILULAS = 40
    ALTURA_POR_PILULA = 68
    n_acoes = len(contagem_acoes) if not contagem_acoes.empty else 1
    altura_compartilhada = ALTURA_BASE_PILULAS + n_acoes * ALTURA_POR_PILULA

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<h3 class="section-title">Top 10 setores mais gerados</h3>', unsafe_allow_html=True)
        top_setores = (gerou_base["setor_gerado"].value_counts() * MULTIPLICADOR).head(10).sort_values()
        if not top_setores.empty:
            fig_setores = px.bar(
                x=top_setores.values, y=top_setores.index, orientation="h",
                labels={"x": "Bases geradas", "y": ""},
                text=[fmt_num(v) for v in top_setores.values],
            )
            fig_setores.update_traces(marker_color=INK, textposition="outside", textfont=dict(color="#000000", size=11))
            base_layout(fig_setores, altura=altura_compartilhada)
            fig_setores.update_xaxes(
                visible=False, showticklabels=False, showgrid=False, zeroline=False,
                range=[0, top_setores.values.max() * 1.18],
            )
            fig_setores.update_yaxes(showgrid=False, zeroline=False)
            st.plotly_chart(fig_setores, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhuma base gerada (ação 'gerou_base') para os filtros selecionados.")

    with col_b:
        st.markdown('<h3 class="section-title">Ações realizadas</h3>', unsafe_allow_html=True)
        if not contagem_acoes.empty:
            total_acoes = contagem_acoes.sum()
            cor_barra = "#3E7CB1"  # mesma cor pra todas as barras, sem destaque

            linhas_html = [f'<div class="acoes-pilula-lista" style="min-height:{altura_compartilhada}px;">']
            for nome_acao, valor in contagem_acoes.items():
                pct = (valor / total_acoes * 100) if total_acoes else 0
                largura = max(pct, 5)  # largura proporcional ao percentual real (escala 0-100%); o piso é só pra não virar uma linha reta quando o valor é quase zero, o texto continua legível graças ao min-width:fit-content do CSS
                linhas_html.append(
                    f'<div class="acao-pilula-item">'
                    f'<div class="acao-pilula-label">{nome_acao}</div>'
                    f'<div class="acao-pilula-barra" style="width:{largura:.1f}%; background:{cor_barra};">'
                    f'<span class="acao-pilula-valor">{fmt_num(valor)}</span>'
                    f'<span class="acao-pilula-pct">{fmt_num(pct, 2)}%</span>'
                    f'</div>'
                    f'</div>'
                )
            linhas_html.append("</div>")

            st.markdown("".join(linhas_html), unsafe_allow_html=True)
        else:
            st.info("Nenhuma ação para os filtros selecionados.")

    # ── Gráficos: dispositivo + anomalia/drift ──────────────────────────────
    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown('<h3 class="section-title">Sessões por dispositivo</h3>', unsafe_allow_html=True)
        contagem_disp = (ses["dispositivo"].value_counts() * MULTIPLICADOR) if "dispositivo" in ses.columns else pd.Series(dtype=int)
        if not contagem_disp.empty:
            fig_disp = px.bar(
                x=contagem_disp.index, y=contagem_disp.values, labels={"x": "", "y": "Sessões"},
                text=[fmt_num(v) for v in contagem_disp.values],
            )
            fig_disp.update_traces(marker_color=GREEN, textposition="outside", textfont=dict(color="#000000", size=11))
            base_layout(fig_disp)
            fig_disp.update_yaxes(
                visible=False, showticklabels=False, showgrid=False, zeroline=False,
                range=[0, contagem_disp.values.max() * 1.18],
            )
            st.plotly_chart(fig_disp, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Sem dados de dispositivo para o período selecionado.")

    with col_d:
        st.markdown('<h3 class="section-title">Uso dos modos especiais</h3>', unsafe_allow_html=True)
        anomalia_pct = (gerou_base["anomalia_ativada"] == "sim").mean() * 100 if not gerou_base.empty else 0
        drift_pct = (gerou_base["deriva_temporal_ativada"] == "sim").mean() * 100 if not gerou_base.empty else 0
        valores_modos = [anomalia_pct, drift_pct]
        fig_modos = px.bar(
            x=["Anomalias", "Deriva Temporal"], y=valores_modos,
            labels={"x": "", "y": "% das bases geradas"},
            text=[f"{v:.1f}%" for v in valores_modos],
        )
        fig_modos.update_traces(marker_color=RUST, textposition="outside", textfont=dict(color="#000000", size=11))
        base_layout(fig_modos)
        maior_valor = max(valores_modos) if max(valores_modos) > 0 else 1
        fig_modos.update_yaxes(
            visible=False, showticklabels=False, showgrid=False, zeroline=False,
            range=[0, maior_valor * 1.18],
        )
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
