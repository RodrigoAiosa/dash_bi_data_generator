"""
data.py: Leitura e transformação dos dados de acesso (log_sessoes e
log_eventos), direto da planilha Google Sheets publicada.
"""
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

_ID_PADRAO = "1iyqlaK2mPLDtojqYOUHagTMXlm4-5XT1gZlY26WXor0"


def sheet_id() -> str:
    """Retorna o ID da planilha configurado no st.secrets ou o ID padrão."""
    return st.secrets.get("controle_acesso_sheet_id", _ID_PADRAO)


def url_aba(nome_aba: str) -> str:
    """
    URL pública de leitura de uma aba específica pelo nome (formato CSV).
    A planilha precisa estar pública na web ou compartilhada via link.
    """
    return f"https://docs.google.com/spreadsheets/d/{sheet_id()}/gviz/tq?tqx=out:csv&sheet={nome_aba}"


@st.cache_data(ttl=900, show_spinner="Carregando dados da planilha...")
def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame, dt.datetime]:
    """Lê as duas abas e devolve (sessoes, eventos, quando_carregou) tratados."""
    sessoes = pd.read_csv(url_aba("log_sessoes"))
    eventos = pd.read_csv(url_aba("log_eventos"))

    # Conversão de timestamps
    sessoes["data_hora"] = pd.to_datetime(sessoes["data_hora"], errors="coerce")
    eventos["data_hora_evento"] = pd.to_datetime(eventos["data_hora_evento"], errors="coerce")

    # Extração de componentes temporais para filtros
    eventos["ano"] = eventos["data_hora_evento"].dt.year
    eventos["mes"] = eventos["data_hora_evento"].dt.month
    eventos["dia"] = eventos["data_hora_evento"].dt.date

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
