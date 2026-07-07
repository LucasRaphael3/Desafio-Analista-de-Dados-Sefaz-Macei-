"""
Passo 3 — Configuração do banco analítico DuckDB

Carrega o arquivo finbra_consolidado.parquet em um banco DuckDB persistente
(finbra.duckdb) e materializa views pré-calculadas que aceleram as consultas
da etapa de análise.

Por que DuckDB?
- Roda in-process, sem servidor para instalar ou configurar.
- Consulta Parquet/CSV diretamente via SQL com vetorização colunar.
- Suporta janelas, pivots e funções analíticas que simplificam as queries.
- Performance superior a pandas para agregações em datasets deste porte.
"""

import duckdb
from pathlib import Path

ROOT = Path(__file__).parent
PARQUET = ROOT / "finbra_consolidado.parquet"
DB_PATH = ROOT / "finbra.duckdb"


def criar_banco() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB_PATH))
    con.execute("SET memory_limit='1GB'")
    return con


def criar_views(con: duckdb.DuckDBPyConnection) -> None:
    """
    Registra o Parquet como tabela e cria views temáticas.

    As views filtram 'agregado' fora do tipo_conta para evitar dupla contagem
    dos totalizadores que o Siconfi inclui no arquivo (ex: 'Despesas Exceto
    Intraorçamentárias'), conforme orientação do próprio enunciado do desafio.
    """

    # Tabela base — lê direto do Parquet; DuckDB mantém referência lazy.
    con.execute(f"""
        CREATE OR REPLACE VIEW finbra AS
        SELECT * FROM read_parquet('{PARQUET.as_posix()}')
    """)

    # Apenas linhas de função (excluindo subfunções e agregados).
    con.execute("""
        CREATE OR REPLACE VIEW funcoes AS
        SELECT *
        FROM finbra
        WHERE tipo_conta = 'funcao'
          AND NOT conta LIKE 'FU%'
    """)

    # Pivot de estágios por capital/função/ano — base para taxa de execução.
    con.execute("""
        CREATE OR REPLACE VIEW execucao AS
        SELECT
            uf,
            ano,
            conta AS funcao,
            SUM(CASE WHEN estagio = 'Despesas Empenhadas' THEN valor ELSE 0 END) AS empenhado,
            SUM(CASE WHEN estagio = 'Despesas Liquidadas' THEN valor ELSE 0 END) AS liquidado,
            SUM(CASE WHEN estagio = 'Despesas Pagas'      THEN valor ELSE 0 END) AS pago,
            MAX(populacao) AS populacao,
            CASE
                WHEN SUM(CASE WHEN estagio = 'Despesas Empenhadas' THEN valor ELSE 0 END) > 0
                THEN ROUND(
                    SUM(CASE WHEN estagio = 'Despesas Pagas' THEN valor ELSE 0 END) /
                    SUM(CASE WHEN estagio = 'Despesas Empenhadas' THEN valor ELSE 0 END) * 100,
                    2
                )
                ELSE NULL
            END AS taxa_execucao
        FROM funcoes
        GROUP BY uf, ano, conta
    """)

    # Evolução de Maceió vs. média das capitais por função e ano.
    # Restringe a 2020-2024 para excluir o 2025 incompleto (11/26 capitais).
    con.execute("""
        CREATE OR REPLACE VIEW maceio_vs_media AS
        SELECT
            ano,
            funcao,
            MAX(CASE WHEN uf = 'AL' THEN empenhado END)               AS maceio_empenhado,
            MAX(CASE WHEN uf = 'AL' THEN pago END)                     AS maceio_pago,
            MAX(CASE WHEN uf = 'AL' THEN taxa_execucao END)            AS maceio_taxa,
            AVG(empenhado)                                              AS media_empenhado,
            AVG(pago)                                                   AS media_pago,
            AVG(taxa_execucao)                                          AS media_taxa
        FROM execucao
        WHERE ano BETWEEN 2020 AND 2024
        GROUP BY ano, funcao
    """)

    print("Views criadas: finbra, funcoes, execucao, maceio_vs_media")


def validar(con: duckdb.DuckDBPyConnection) -> None:
    """Queries de sanidade para confirmar integridade dos dados."""

    total = con.execute("SELECT COUNT(*) FROM finbra").fetchone()[0]
    capitais_2024 = con.execute(
        "SELECT COUNT(DISTINCT uf) FROM finbra WHERE ano = 2024"
    ).fetchone()[0]
    capitais_2025 = con.execute(
        "SELECT COUNT(DISTINCT uf) FROM finbra WHERE ano = 2025"
    ).fetchone()[0]
    maior_empenho = con.execute("""
        SELECT uf, funcao, empenhado
        FROM execucao
        WHERE ano = 2024
        ORDER BY empenhado DESC
        LIMIT 1
    """).fetchone()

    print(f"\nValidação do banco:")
    print(f"  Total de linhas    : {total:,}")
    print(f"  Capitais em 2024   : {capitais_2024}/26")
    print(f"  Capitais em 2025   : {capitais_2025}/26  <- dado parcial")
    print(f"  Maior empenho 2024 : {maior_empenho[0]} | {maior_empenho[1]} "
          f"| R$ {maior_empenho[2]:,.0f}")


def main() -> None:
    print(f"Conectando ao banco: {DB_PATH.name}")
    con = criar_banco()
    criar_views(con)
    validar(con)
    con.close()
    print(f"\nBanco salvo em: {DB_PATH.name}")


if __name__ == "__main__":
    main()
