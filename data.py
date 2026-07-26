"""
data.py: Leitura e transformação dos dados de acesso (log_sessoes e
log_eventos), direto da planilha Google Sheets publicada.
"""
import pandas as pd
import streamlit as st

_ID_PADRAO = "1iyqlaK2mPLDtojqYOUHagTMXlm4-5XT1gZlY26WXor0"


def sheet_id() -> str:
    return st.secrets.get("controle_acesso_sheet_id", _ID_PADRAO)


def url_aba(nome_aba: str) -> str:
    """
    URL pública de leitura de uma aba específica, pelo nome (não precisa
    saber o gid numérico). A planilha precisa estar compartilhada como
    "Qualquer pessoa com o link pode visualizar" (ou publicada na web).
    """
    return f"https://docs.google.com/spreadsheets/d/{sheet_id()}/gviz/tq?tqx=out:csv&sheet={nome_aba}"


@st.cache_data(ttl=300, show_spinner="Carregando dados da planilha...")
def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame, "datetime"]:
    """Lê as duas abas e devolve (sessoes, eventos, quando_carregou) já com colunas de data tratadas."""
    import datetime as _dt
    from zoneinfo import ZoneInfo

    sessoes = pd.read_csv(url_aba("log_sessoes"))
    eventos = pd.read_csv(url_aba("log_eventos"))

    sessoes["data_hora"] = pd.to_datetime(sessoes["data_hora"], errors="coerce")
    eventos["data_hora_evento"] = pd.to_datetime(eventos["data_hora_evento"], errors="coerce")

    eventos["ano"] = eventos["data_hora_evento"].dt.year
    eventos["mes"] = eventos["data_hora_evento"].dt.month
    eventos["dia"] = eventos["data_hora_evento"].dt.date

    quando_carregou = _dt.datetime.now(ZoneInfo("America/Sao_Paulo"))

    return sessoes, eventos, quando_carregou


def duracao_para_segundos(duracao_str) -> float | None:
    """Converte 'HH:MM:SS' em segundos. Devolve None se o formato for inválido."""
    try:
        h, m, s = str(duracao_str).split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return None
