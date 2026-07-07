"""
Passo 4 — Análise de Indicadores e Geração de Gráficos

Produz 6 visualizações salvas em saidas/graficos/, a partir do banco DuckDB
configurado no passo 3. Todas as análises usam apenas o período 2020-2024
(anos completos com 26 capitais); 2025 é excluído por estar incompleto.

Indicadores calculados:
  1. Taxa de Execução média por capital (Pago / Empenhado × 100)
  2. Ranking de Saúde per capita — empenhado vs pago (2024)
  3. Ranking de Educação per capita — empenhado vs pago (2024)
  4. Evolução de Maceió vs. média das capitais em Saúde e Educação
  5. Heatmap de taxa de execução por função e capital (2024)
  6. Concentração das subfunções de Saúde em Maceió (2024)
"""

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).parent
DB_PATH = ROOT / "finbra.duckdb"
PARQUET = ROOT / "finbra_consolidado.parquet"
DIR_GRAFICOS = ROOT / "saidas" / "graficos"
DIR_GRAFICOS.mkdir(parents=True, exist_ok=True)

# Paleta e estilo globais
CINZA_FUNDO = "#1a1a2e"
AZUL_ACENTO = "#4cc9f0"
ROSA_ACENTO = "#f72585"
VERDE_ACENTO = "#06d6a0"
AMARELO_ACENTO = "#ffd166"
COR_MACEIO = "#f72585"
COR_MEDIA = "#4cc9f0"

plt.rcParams.update(
    {
        "figure.facecolor": CINZA_FUNDO,
        "axes.facecolor": "#16213e",
        "axes.edgecolor": "#30475e",
        "axes.labelcolor": "#e0e0e0",
        "xtick.color": "#e0e0e0",
        "ytick.color": "#e0e0e0",
        "text.color": "#e0e0e0",
        "grid.color": "#30475e",
        "grid.linestyle": "--",
        "grid.alpha": 0.5,
        "font.family": "DejaVu Sans",
        "axes.titlesize": 13,
        "axes.labelsize": 11,
    }
)

BILHAO = 1_000_000_000
MILHAO = 1_000_000


def fmt_bilhao(x, _):
    return f"R$ {x/BILHAO:.1f}B"


def fmt_pct(x, _):
    return f"{x:.0f}%"


def conectar() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


# ---------------------------------------------------------------------------
# Gráfico 1 — Taxa de execução média por capital (2020-2024)
# ---------------------------------------------------------------------------
def grafico_taxa_execucao_media(con: duckdb.DuckDBPyConnection) -> None:
    df = con.execute("""
        SELECT
            uf,
            ROUND(AVG(taxa_execucao), 1) AS taxa_media,
            CASE WHEN uf = 'AL' THEN 1 ELSE 0 END AS destaque
        FROM execucao
        WHERE ano BETWEEN 2020 AND 2024
          AND taxa_execucao IS NOT NULL
        GROUP BY uf
        ORDER BY taxa_media DESC
    """).df()

    cores = [COR_MACEIO if d else AZUL_ACENTO for d in df["destaque"]]

    fig, ax = plt.subplots(figsize=(14, 6))
    bars = ax.bar(df["uf"], df["taxa_media"], color=cores, width=0.65, zorder=3)

    # Linha de referência a 100%
    ax.axhline(100, color=AMARELO_ACENTO, linewidth=1.2, linestyle="--", alpha=0.8)
    ax.text(len(df) - 0.5, 101, "100%", color=AMARELO_ACENTO, fontsize=9, ha="right")

    # Rótulos sobre as barras
    for bar, val in zip(bars, df["taxa_media"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.4,
            f"{val:.0f}%",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#e0e0e0",
        )

    ax.set_title(
        "Taxa de Execução Financeira Média por Capital  |  2020–2024\n"
        "( Despesas Pagas ÷ Despesas Empenhadas × 100 )",
        pad=14,
    )
    ax.set_xlabel("Capital (UF)")
    ax.set_ylabel("Taxa média (%)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_pct))
    ax.set_ylim(0, max(df["taxa_media"]) * 1.12)
    ax.grid(axis="y", zorder=0)

    # Legenda manual
    from matplotlib.patches import Patch
    legenda = [
        Patch(color=COR_MACEIO, label="Maceió (AL)"),
        Patch(color=AZUL_ACENTO, label="Demais capitais"),
    ]
    ax.legend(handles=legenda, loc="upper right", framealpha=0.2)

    fig.tight_layout()
    caminho = DIR_GRAFICOS / "01_taxa_execucao_capitais.png"
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Salvo: {caminho.name}")


# ---------------------------------------------------------------------------
# Gráfico 2 — Saúde per capita: empenhado vs pago (2024)
# ---------------------------------------------------------------------------
def grafico_saude_per_capita(con: duckdb.DuckDBPyConnection) -> None:
    df = con.execute("""
        SELECT
            uf,
            empenhado / populacao AS emp_pc,
            pago / populacao      AS pago_pc
        FROM execucao
        WHERE ano = 2024
          AND funcao LIKE '10 -%'
          AND populacao > 0
        ORDER BY emp_pc DESC
    """).df()

    _grafico_per_capita_duplo(
        df,
        titulo="Saúde — Gasto per Capita por Capital  |  2024",
        nome_arquivo="02_saude_per_capita_2024.png",
        cor_emp=VERDE_ACENTO,
        cor_pago=AZUL_ACENTO,
    )


# ---------------------------------------------------------------------------
# Gráfico 3 — Educação per capita: empenhado vs pago (2024)
# ---------------------------------------------------------------------------
def grafico_educacao_per_capita(con: duckdb.DuckDBPyConnection) -> None:
    df = con.execute("""
        SELECT
            uf,
            empenhado / populacao AS emp_pc,
            pago / populacao      AS pago_pc
        FROM execucao
        WHERE ano = 2024
          AND funcao LIKE '12 -%'
          AND populacao > 0
        ORDER BY emp_pc DESC
    """).df()

    _grafico_per_capita_duplo(
        df,
        titulo="Educação — Gasto per Capita por Capital  |  2024",
        nome_arquivo="03_educacao_per_capita_2024.png",
        cor_emp=AMARELO_ACENTO,
        cor_pago=ROSA_ACENTO,
    )


def _grafico_per_capita_duplo(
    df: pd.DataFrame, titulo: str, nome_arquivo: str, cor_emp: str, cor_pago: str
) -> None:
    x = np.arange(len(df))
    largura = 0.38

    fig, ax = plt.subplots(figsize=(16, 6))
    barras_emp = ax.bar(x - largura / 2, df["emp_pc"], largura,
                        color=cor_emp, alpha=0.9, label="Empenhado", zorder=3)
    barras_pago = ax.bar(x + largura / 2, df["pago_pc"], largura,
                         color=cor_pago, alpha=0.9, label="Pago", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(df["uf"], fontsize=9)

    # Destaque Maceió
    idx_al = df[df["uf"] == "AL"].index
    if len(idx_al):
        pos = df.index.get_loc(idx_al[0])
        ax.axvspan(pos - 0.6, pos + 0.6, color=COR_MACEIO, alpha=0.08, zorder=0)
        ax.text(pos, df["emp_pc"].max() * 1.02, "Maceió",
                ha="center", color=COR_MACEIO, fontsize=9, fontweight="bold")

    ax.set_title(titulo, pad=14)
    ax.set_xlabel("Capital (UF)")
    ax.set_ylabel("R$ por habitante")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"R$ {v:,.0f}"))
    ax.legend(framealpha=0.2)
    ax.grid(axis="y", zorder=0)

    fig.tight_layout()
    caminho = DIR_GRAFICOS / nome_arquivo
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Salvo: {caminho.name}")


# ---------------------------------------------------------------------------
# Gráfico 4 — Evolução Maceió vs. média das capitais em Saúde e Educação
# ---------------------------------------------------------------------------
def grafico_evolucao_maceio(con: duckdb.DuckDBPyConnection) -> None:
    df = con.execute("""
        SELECT
            ano,
            funcao,
            maceio_empenhado,
            maceio_pago,
            media_empenhado,
            media_pago
        FROM maceio_vs_media
        WHERE funcao IN ('10 - Sa\xfade', '12 - Educa\xe7\xe3o')
        ORDER BY funcao, ano
    """).df()

    # Fallback: busca pelos códigos se os nomes com acento não baterem
    if df.empty:
        df = con.execute("""
            SELECT
                ano,
                funcao,
                maceio_empenhado,
                maceio_pago,
                media_empenhado,
                media_pago
            FROM maceio_vs_media
            WHERE funcao LIKE '10 -%' OR funcao LIKE '12 -%'
            ORDER BY funcao, ano
        """).df()

    funcoes_unicas = sorted(df["funcao"].unique())
    fig, axes = plt.subplots(1, len(funcoes_unicas), figsize=(16, 6), sharey=False)
    if len(funcoes_unicas) == 1:
        axes = [axes]

    for ax, funcao in zip(axes, funcoes_unicas):
        sub = df[df["funcao"] == funcao].sort_values("ano")

        ax.plot(sub["ano"], sub["maceio_empenhado"] / MILHAO,
                color=COR_MACEIO, marker="o", linewidth=2, label="Maceió — Empenhado")
        ax.plot(sub["ano"], sub["maceio_pago"] / MILHAO,
                color=COR_MACEIO, marker="o", linewidth=2, linestyle="--", label="Maceió — Pago")
        ax.plot(sub["ano"], sub["media_empenhado"] / MILHAO,
                color=COR_MEDIA, marker="s", linewidth=2, label="Média — Empenhado")
        ax.plot(sub["ano"], sub["media_pago"] / MILHAO,
                color=COR_MEDIA, marker="s", linewidth=2, linestyle="--", label="Média — Pago")

        ax.fill_between(
            sub["ano"],
            sub["maceio_empenhado"] / MILHAO,
            sub["maceio_pago"] / MILHAO,
            alpha=0.12, color=COR_MACEIO,
        )

        rotulo = funcao.split(" - ", 1)[-1] if " - " in funcao else funcao
        ax.set_title(rotulo, pad=10)
        ax.set_xlabel("Ano")
        ax.set_ylabel("R$ (milhões)")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"R$ {v:,.0f}M"))
        ax.set_xticks(sub["ano"])
        ax.grid(axis="y")
        ax.legend(fontsize=8, framealpha=0.2)

    fig.suptitle(
        "Evolução do Gasto: Maceió vs. Média das Capitais  |  2020–2024",
        fontsize=14,
        y=1.02,
    )
    fig.tight_layout()
    caminho = DIR_GRAFICOS / "04_evolucao_maceio.png"
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Salvo: {caminho.name}")


# ---------------------------------------------------------------------------
# Gráfico 5 — Heatmap de taxa de execução por função × capital (2024)
# ---------------------------------------------------------------------------
def grafico_heatmap_execucao(con: duckdb.DuckDBPyConnection) -> None:
    # Seleciona as funções com maior volume total de empenhado em 2024
    top_funcoes = con.execute("""
        SELECT funcao
        FROM execucao
        WHERE ano = 2024
        GROUP BY funcao
        ORDER BY SUM(empenhado) DESC
        LIMIT 12
    """).df()["funcao"].tolist()

    placeholders = ", ".join(f"'{f}'" for f in top_funcoes)
    df = con.execute(f"""
        SELECT uf, funcao, taxa_execucao
        FROM execucao
        WHERE ano = 2024
          AND funcao IN ({placeholders})
    """).df()

    pivot = df.pivot(index="uf", columns="funcao", values="taxa_execucao")
    # Ordena capitais pela taxa média
    pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]
    # Encurta rótulos das funções
    pivot.columns = [c.split(" - ", 1)[-1] if " - " in c else c for c in pivot.columns]

    fig, ax = plt.subplots(figsize=(16, 10))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="RdYlGn",
        annot=True,
        fmt=".0f",
        linewidths=0.4,
        linecolor="#1a1a2e",
        cbar_kws={"label": "Taxa de Execução (%)"},
        vmin=50,
        vmax=100,
    )
    ax.set_title(
        "Taxa de Execução Financeira por Função e Capital  |  2024\n"
        "( % do Empenhado que foi efetivamente Pago )",
        pad=14,
    )
    ax.set_xlabel("Função orçamentária")
    ax.set_ylabel("Capital (UF)")
    ax.tick_params(axis="x", rotation=30)

    fig.tight_layout()
    caminho = DIR_GRAFICOS / "05_heatmap_execucao.png"
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Salvo: {caminho.name}")


# ---------------------------------------------------------------------------
# Gráfico 6 — Subfunções de Saúde em Maceió (2024)
# ---------------------------------------------------------------------------
def grafico_subfuncoes_saude_maceio(con: duckdb.DuckDBPyConnection) -> None:
    df = con.execute("""
        SELECT
            conta AS subfuncao,
            SUM(CASE WHEN estagio = 'Despesas Empenhadas' THEN valor ELSE 0 END) AS empenhado,
            SUM(CASE WHEN estagio = 'Despesas Pagas'      THEN valor ELSE 0 END) AS pago
        FROM finbra
        WHERE uf = 'AL'
          AND ano = 2024
          AND tipo_conta = 'subfuncao'
          AND conta LIKE '10.%'
        GROUP BY conta
        ORDER BY empenhado DESC
    """).df()

    if df.empty:
        print("  Nenhuma subfunção de Saúde encontrada para Maceió/2024. Pulando.")
        return

    # Limpa rótulo: "10.301 - Atenção Básica" → "Atenção Básica (10.301)"
    def formatar(s):
        partes = str(s).split(" - ", 1)
        if len(partes) == 2:
            return f"{partes[1]}\n({partes[0]})"
        return s

    df["label"] = df["subfuncao"].map(formatar)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(df))
    largura = 0.38

    ax.bar(x - largura / 2, df["empenhado"] / MILHAO,
           largura, color=VERDE_ACENTO, alpha=0.9, label="Empenhado", zorder=3)
    ax.bar(x + largura / 2, df["pago"] / MILHAO,
           largura, color=AZUL_ACENTO, alpha=0.9, label="Pago", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(df["label"], fontsize=8.5)
    ax.set_title("Subfunções de Saúde — Maceió (AL)  |  2024", pad=14)
    ax.set_xlabel("Subfunção")
    ax.set_ylabel("R$ (milhões)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"R$ {v:,.0f}M"))
    ax.legend(framealpha=0.2)
    ax.grid(axis="y", zorder=0)

    fig.tight_layout()
    caminho = DIR_GRAFICOS / "06_subfuncoes_saude_maceio.png"
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Salvo: {caminho.name}")


# ---------------------------------------------------------------------------
# Tabelas de texto para o README
# ---------------------------------------------------------------------------
def imprimir_tabelas(con: duckdb.DuckDBPyConnection) -> None:
    print("\n--- TABELA: Taxa de Execução Média por Capital (2020-2024) ---")
    df = con.execute("""
        SELECT uf,
               ROUND(AVG(taxa_execucao), 1) AS taxa_media
        FROM execucao
        WHERE ano BETWEEN 2020 AND 2024
          AND taxa_execucao IS NOT NULL
        GROUP BY uf
        ORDER BY taxa_media DESC
    """).df()
    print(df.to_string(index=False))

    print("\n--- TABELA: Saúde per capita 2024 (empenhado) ---")
    df2 = con.execute("""
        SELECT uf,
               ROUND(empenhado / populacao, 2) AS emp_pc,
               ROUND(pago / populacao, 2)       AS pago_pc,
               ROUND(taxa_execucao, 1)           AS taxa
        FROM execucao
        WHERE ano = 2024 AND funcao LIKE '10 -%' AND populacao > 0
        ORDER BY emp_pc DESC
    """).df()
    print(df2.to_string(index=False))

    print("\n--- TABELA: Evolução Maceió — Saúde (2020-2024) ---")
    df3 = con.execute("""
        SELECT ano,
               ROUND(maceio_empenhado / 1e6, 1) AS mac_emp_M,
               ROUND(maceio_pago / 1e6, 1)       AS mac_pago_M,
               ROUND(maceio_taxa, 1)              AS mac_taxa,
               ROUND(media_empenhado / 1e6, 1)   AS med_emp_M,
               ROUND(media_taxa, 1)               AS med_taxa
        FROM maceio_vs_media
        WHERE funcao LIKE '10 -%'
        ORDER BY ano
    """).df()
    print(df3.to_string(index=False))


def main() -> None:
    print(f"Conectando ao banco: {DB_PATH.name}")
    con = conectar()

    print("\nGerando gráficos...")
    grafico_taxa_execucao_media(con)
    grafico_saude_per_capita(con)
    grafico_educacao_per_capita(con)
    grafico_evolucao_maceio(con)
    grafico_heatmap_execucao(con)
    grafico_subfuncoes_saude_maceio(con)

    imprimir_tabelas(con)
    con.close()

    print(f"\nAnálise concluída. Gráficos salvos em: {DIR_GRAFICOS}")


if __name__ == "__main__":
    main()
