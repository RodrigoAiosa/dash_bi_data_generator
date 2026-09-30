"""
data.py: Leitura e transformação dos dados de acesso, direto da tabela
public.logs_uso do Supabase (PostgreSQL).

A tabela guarda dois tipos de linha, separados pela coluna tipo_evento:
- 'sessao_inicio': uma por acesso (dispositivo, navegador, idioma)
- 'clique': uma por ação realizada (gerou_base, baixou_zip etc.)

Este módulo devolve os mesmos dois DataFrames (sessoes, eventos) e com as
mesmas colunas que o app.py já usava quando lia o Google Sheets.
"""
import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg
import streamlit as st

_SQL_LOGS = """
    select id_sessao, tipo_evento, acao, setor_gerado, volume_linhas,
           anomalia_ativada, deriva_temporal_ativada, status, erro_detalhe,
           dispositivo, navegador, idioma_interface, duracao_segundos,
           data_hora_evento
      from public.logs_uso
"""


def _conectar() -> psycopg.Connection:
    """Abre a conexão usando os dados de [supabase] no st.secrets."""
    cfg = st.secrets["supabase"]
    return psycopg.connect(
        host=cfg["host"],
        port=int(cfg.get("port", 5432)),
        dbname=cfg.get("dbname", "postgres"),
        user=cfg["user"],
        password=cfg["password"],
        sslmode=cfg.get("sslmode", "require"),
        connect_timeout=15,
    )


def _ler_logs() -> pd.DataFrame:
    with _conectar() as conn, conn.cursor() as cur:
        cur.execute(_SQL_LOGS)
        colunas = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=colunas)


def _segundos_para_hms(segundos) -> str | None:
    if pd.isna(segundos):
        return None
    segundos = int(segundos)
    return f"{segundos // 3600:02d}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"


def montar_sessoes_eventos(logs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa logs_uso em (sessoes, eventos) no formato esperado pelo app.py."""
    logs = logs.copy()
    logs["data_hora_evento"] = pd.to_datetime(logs["data_hora_evento"], errors="coerce")

    # Sessões: uma linha por 'sessao_inicio'
    sessoes = (
        logs[logs["tipo_evento"] == "sessao_inicio"]
        .rename(columns={"data_hora_evento": "data_hora"})
        [["id_sessao", "data_hora", "dispositivo", "navegador", "idioma_interface"]]
        .drop_duplicates("id_sessao")
        .reset_index(drop=True)
    )

    # Duração da sessão = maior duracao_segundos entre os cliques dela
    # (duracao_segundos é o tempo desde o início da sessão até o clique)
    dur_max = logs.groupby("id_sessao")["duracao_segundos"].max()
    sessoes["duracao"] = sessoes["id_sessao"].map(dur_max).map(_segundos_para_hms)

    # Eventos: uma linha por 'clique'
    eventos = logs[logs["tipo_evento"] == "clique"].drop(
        columns=["tipo_evento", "dispositivo", "navegador", "idioma_interface"]
    ).reset_index(drop=True)

    # O app compara os modos especiais com "sim" (formato da planilha antiga)
    for col in ("anomalia_ativada", "deriva_temporal_ativada"):
        eventos[col] = eventos[col].map({True: "sim", False: "não"})

    eventos["volume_linhas"] = pd.to_numeric(eventos["volume_linhas"], errors="coerce")

    # Componentes temporais para os filtros
    eventos["ano"] = eventos["data_hora_evento"].dt.year
    eventos["mes"] = eventos["data_hora_evento"].dt.month
    eventos["dia"] = eventos["data_hora_evento"].dt.date

    return sessoes, eventos


@st.cache_data(ttl=900, show_spinner="Carregando dados do Supabase...")
def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame, dt.datetime]:
    """Lê logs_uso e devolve (sessoes, eventos, quando_carregou) tratados."""
    sessoes, eventos = montar_sessoes_eventos(_ler_logs())
    quando_carregou = dt.datetime.now(ZoneInfo("America/Sao_Paulo"))
    return sessoes, eventos, quando_carregou


def duracao_para_segundos(duracao_str) -> float | None:
    """Converte 'HH:MM:SS' em segundos. Retorna None se inválido ou ausente."""
    if pd.isna(duracao_str) or not duracao_str:
        return None
    try:
        partes = str(duracao_str).strip().split(":")
        if len(partes) == 3:
            h, m, s = partes
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(partes) == 2:
            m, s = partes
            return int(m) * 60 + float(s)
    except Exception:
        pass
    return None
