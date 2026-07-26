
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
N_SESSOES = 100_000
N_EVENTOS_POR_SESSAO_MIN = 1
N_EVENTOS_POR_SESSAO_MAX = 8

ACOES = ["acessou_painel", "gerou_base", "exportou_csv", "visualizou_preview", "aplicou_filtro"]
ACOES_PESOS = [0.15, 0.25, 0.20, 0.25, 0.15]

SETORES = ["Vendas", "Marketing", "Financeiro", "RH", "Operações", "TI", "Logística", "Jurídico", "Compras", "Atendimento"]
SETORES_PESOS = [0.18, 0.15, 0.12, 0.10, 0.12, 0.08, 0.10, 0.05, 0.05, 0.05]

DISPOSITIVOS = ["Desktop", "Mobile", "Tablet"]
DISPOSITIVOS_PESOS = [0.65, 0.30, 0.05]

STATUS_OPCOES = ["sucesso", "erro", "aviso"]
STATUS_PESOS = [0.88, 0.08, 0.04]

DATA_FIM = datetime(2026, 7, 26, 12, 0, 0)
DATA_INICIO = DATA_FIM - timedelta(days=365)

ACOES_LABEL = {
    "acessou_painel": "Acessou Painel",
    "gerou_base": "Gerou Base",
    "exportou_csv": "Exportou CSV",
    "visualizou_preview": "Visualizou Preview",
    "aplicou_filtro": "Aplicou Filtro",
}

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def fmt_num(valor, decimais=0):
    """Formata número com separador de milhar e vírgula decimal."""
    if decimais > 0:
        return f"{valor:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(valor):,}".replace(",", ".")


def duracao_para_segundos(d):
    """Converte string MM:SS para segundos."""
    if pd.isna(d):
        return None
    partes = str(d).split(":")
    if len(partes) == 2:
        return int(partes[0]) * 60 + int(partes[1])
    return None


# =============================================================================
# 1. GERAR SESSÕES
# =============================================================================
print("=" * 70)
print("  SIMULADOR PAINEL BI DATA GENERATOR — 100.000 ACESSOS ÚNICOS")
print("=" * 70)
print("\n🔄 Gerando sessões...")

np.random.seed(42)
random.seed(42)

sessoes_list = []
for i in range(N_SESSOES):
    delta_segundos = random.randint(0, int((DATA_FIM - DATA_INICIO).total_seconds()))
    data_hora = DATA_INICIO + timedelta(seconds=delta_segundos)
    
    duracao_seg = int(np.random.exponential(300) + 30)
    duracao_seg = min(duracao_seg, 2700)
    minutos = duracao_seg // 60
    segundos = duracao_seg % 60
    duracao_str = f"{minutos:02d}:{segundos:02d}"
    
    dispositivo = random.choices(DISPOSITIVOS, weights=DISPOSITIVOS_PESOS)[0]
    
    sessoes_list.append({
        "id_sessao": f"sess_{i+1:08d}",
        "data_hora": data_hora,
        "duracao": duracao_str,
        "dispositivo": dispositivo,
    })

sessoes = pd.DataFrame(sessoes_list)
sessoes = sessoes.sort_values("data_hora").reset_index(drop=True)
print(f"   ✓ {fmt_num(len(sessoes))} sessões geradas")

# =============================================================================
# 2. GERAR EVENTOS
# =============================================================================
print("\n🔄 Gerando eventos...")

eventos_list = []
for _, sess in sessoes.iterrows():
    n_eventos = random.randint(N_EVENTOS_POR_SESSAO_MIN, N_EVENTOS_POR_SESSAO_MAX)
    duracao_total_seg = int(sess["duracao"].split(":")[0]) * 60 + int(sess["duracao"].split(":")[1])
    
    for e in range(n_eventos):
        offset_seg = random.randint(0, max(duracao_total_seg, 1))
        data_hora_evento = sess["data_hora"] + timedelta(seconds=offset_seg)
        
        acao = random.choices(ACOES, weights=ACOES_PESOS)[0]
        setor_gerado = random.choices(SETORES, weights=SETORES_PESOS)[0] if acao == "gerou_base" else None
        
        volume_linhas = None
        if acao == "gerou_base":
            volume_linhas = int(np.random.lognormal(8, 1.5))
            volume_linhas = max(50, min(volume_linhas, 500_000))
        
        status = random.choices(STATUS_OPCOES, weights=STATUS_PESOS)[0]
        
        erro_detalhe = None
        if status == "erro":
            erros = ["Timeout", "Conexão perdida", "Dados inválidos", "Permissão negada", "Memória insuficiente"]
            erro_detalhe = random.choice(erros)
        
        anomalia_ativada = "sim" if acao == "gerou_base" and random.random() < 0.15 else "não"
        deriva_temporal_ativada = "sim" if acao == "gerou_base" and random.random() < 0.10 else "não"
        
        eventos_list.append({
            "id_sessao": sess["id_sessao"],
            "data_hora_evento": data_hora_evento,
            "ano": data_hora_evento.year,
            "mes": data_hora_evento.month,
            "dia": data_hora_evento.date(),
            "acao": acao,
            "setor_gerado": setor_gerado,
            "volume_linhas": volume_linhas,
            "status": status,
            "erro_detalhe": erro_detalhe,
            "anomalia_ativada": anomalia_ativada,
            "deriva_temporal_ativada": deriva_temporal_ativada,
        })

eventos = pd.DataFrame(eventos_list)
eventos = eventos.sort_values("data_hora_evento").reset_index(drop=True)
print(f"   ✓ {fmt_num(len(eventos))} eventos gerados")
print(f"   ✓ Média de {len(eventos)/len(sessoes):.2f} eventos por sessão")

# =============================================================================
# 3. CALCULAR KPIs (idêntico ao app.py)
# =============================================================================
print("\n🔄 Calculando métricas...\n")

total_sessoes = sessoes["id_sessao"].nunique()
total_eventos = len(eventos)

gerou_base = eventos[eventos["acao"] == "gerou_base"]
total_bases = len(gerou_base)
total_linhas = gerou_base["volume_linhas"].fillna(0).sum()
taxa_sucesso = (eventos["status"] == "sucesso").mean() * 100

setor_top = gerou_base["setor_gerado"].mode().iloc[0] if not gerou_base.empty and not gerou_base["setor_gerado"].mode().empty else "-"

duracoes = sessoes["duracao"].dropna().map(duracao_para_segundos).dropna()
duracao_media_seg = duracoes.mean()
duracao_media_fmt = f"{int(duracao_media_seg // 60)}min {int(duracao_media_seg % 60)}s"

contagem_disp = sessoes["dispositivo"].value_counts()
contagem_acoes = eventos["acao"].map(lambda a: ACOES_LABEL.get(a, a)).value_counts()

anomalia_pct = (gerou_base["anomalia_ativada"] == "sim").mean() * 100 if not gerou_base.empty else 0
drift_pct = (gerou_base["deriva_temporal_ativada"] == "sim").mean() * 100 if not gerou_base.empty else 0

top_setores = gerou_base["setor_gerado"].value_counts().head(10)

# =============================================================================
# 4. EXIBIR RESULTADOS
# =============================================================================
print("─" * 70)
print("  📊 PAINEL DE ACESSO: BI DATA GENERATOR")
print("─" * 70)
print(f"\n  Período: {DATA_INICIO.strftime('%d/%m/%Y')} → {DATA_FIM.strftime('%d/%m/%Y')}")

print(f"\n  {'👥 Sessões (acessos únicos):':<35} {fmt_num(total_sessoes):>12}")
print(f"  {'📦 Bases geradas:':<35} {fmt_num(total_bases):>12}")
print(f"  {'📊 Total de linhas geradas:':<35} {fmt_num(total_linhas):>12}")
print(f"  {'✅ Taxa de sucesso:':<35} {fmt_num(taxa_sucesso, 1):>11}%")
print(f"  {'⏱️  Duração média por sessão:':<35} {duracao_media_fmt:>12}")
print(f"  {'🏆 Setor mais gerado:':<35} {str(setor_top)[:18]:>12}")

print(f"\n  {'📱 SESSÕES POR DISPOSITIVO':<35}")
print(f"  {'─' * 47}")
for disp, qtd in contagem_disp.items():
    pct = qtd / total_sessoes * 100
    print(f"  {'   ' + disp:<32} {fmt_num(qtd):>7}  ({pct:.1f}%)")

print(f"\n  {'🎯 AÇÕES REALIZADAS':<35}")
print(f"  {'─' * 47}")
for acao, qtd in contagem_acoes.items():
    pct = qtd / total_eventos * 100
    print(f"  {'   ' + acao:<32} {fmt_num(qtd):>7}  ({pct:.1f}%)")

print(f"\n  {'🔥 TOP 10 SETORES (bases geradas)':<35}")
print(f"  {'─' * 47}")
for i, (setor, qtd) in enumerate(top_setores.items(), 1):
    print(f"  {'   ' + f'{i:2d}. {setor}':<32} {fmt_num(qtd):>7}")

print(f"\n  {'⚡ MODOS ESPECIAIS (% das bases)':<35}")
print(f"  {'─' * 47}")
print(f"  {'   Anomalias ativadas:':<32} {fmt_num(anomalia_pct, 1):>7}%")
print(f"  {'   Deriva temporal:':<32} {fmt_num(drift_pct, 1):>7}%")

print(f"\n  {'📈 ESTATÍSTICAS ADICIONAIS':<35}")
print(f"  {'─' * 47}")
print(f"  {'   Total de eventos:':<32} {fmt_num(total_eventos):>7}")
print(f"  {'   Eventos/sessão (média):':<32} {fmt_num(total_eventos/total_sessoes, 2):>7}")
print(f"  {'   Linhas médias/base:':<32} {fmt_num(total_linhas/total_bases, 0):>7}")
print(f"  {'   Taxa de erro:':<32} {fmt_num((eventos['status']=='erro').mean()*100, 1):>6}%")
print(f"  {'   Taxa de aviso:':<32} {fmt_num((eventos['status']=='aviso').mean()*100, 1):>6}%")

print("\n" + "=" * 70)
print("  ✅ Simulação concluída! Nenhum arquivo foi salvo.")
print("=" * 70)
'''

# Salvar o script
output_path = "/mnt/agents/output/simulador_painel_100k.py"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(script_content)

print(f"✓ Script salvo em: {output_path}")
print(f"  Tamanho: {len(script_content):,} caracteres")
