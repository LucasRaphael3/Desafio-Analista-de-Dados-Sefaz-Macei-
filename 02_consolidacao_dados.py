import re
import sys
from pathlib import Path

import pandas as pd

DADOS_EXTRAIDOS = Path(__file__).parent / "dados_extraidos"
SAIDA_PARQUET = Path(__file__).parent / "finbra_consolidado.parquet"

# Renomeia as colunas usando posição, evitando dependência dos acentos do cabeçalho
# original (que variam sutilmente entre os arquivos de anos diferentes).
COLUNAS_RENOMEADAS = [
    "instituicao",
    "cod_ibge",
    "uf",
    "populacao",
    "estagio",
    "conta",
    "id_conta",
    "valor",
]

# Padrões para classificar cada linha da coluna "Conta":
#   função:    "10 - Saúde"         → dois dígitos seguidos de " - "
#   subfunção: "10.301 - Atenção B." → dois dígitos, ponto, três dígitos, " - "
#   agregado:  "Despesas Exceto ...", "FU10 - Demais ..." etc.
RE_FUNCAO = re.compile(r"^\d{2} - ")
RE_SUBFUNCAO = re.compile(r"^\d{2}\.\d{3} - ")
RE_FU_RESTO = re.compile(r"^FU\d+ - ")


def classificar_conta(conta: str) -> str:
    """Retorna o tipo semântico de cada linha da coluna Conta."""
    if pd.isna(conta):
        return "desconhecido"
    s = str(conta)
    if RE_SUBFUNCAO.match(s):
        return "subfuncao"
    if RE_FUNCAO.match(s) or RE_FU_RESTO.match(s):
        return "funcao"
    return "agregado"


def ler_csv_finbra(csv_path: Path, ano: int) -> pd.DataFrame:
    """
    Lê um arquivo finbra.csv respeitando o formato do Siconfi:
      - encoding ISO-8859-1 (padrão de exportação do sistema)
      - separador de colunas: ponto e vírgula
      - separador decimal: vírgula (padrão pt-BR)
      - 3 linhas de metadados antes do cabeçalho real
    """
    df = pd.read_csv(
        csv_path,
        sep=";",
        skiprows=3,
        encoding="latin-1",
        decimal=",",
        thousands=".",
        header=0,
    )

    # Valida número de colunas antes de renomear para detectar variações de layout
    if len(df.columns) != len(COLUNAS_RENOMEADAS):
        raise ValueError(
            f"{csv_path}: esperadas {len(COLUNAS_RENOMEADAS)} colunas, "
            f"encontradas {len(df.columns)}: {list(df.columns)}"
        )
    df.columns = COLUNAS_RENOMEADAS

    # Força tipos corretos e remove espaços residuais
    df["ano"] = ano
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce").astype("Int64")
    df["tipo_conta"] = df["conta"].map(classificar_conta)

    for col in ["instituicao", "uf", "estagio", "conta", "id_conta"]:
        df[col] = df[col].astype(str).str.strip()

    return df


def consolidar() -> pd.DataFrame:
    """
    Localiza todos os finbra.csv dentro de dados_extraidos/, lê cada um,
    adiciona a coluna 'ano' inferida do nome da pasta e concatena tudo.

    Imprime um resumo por ano para alertar sobre anos com menos de 26 capitais
    (dado parcialmente declarado, como é esperado para 2025).
    """
    csv_paths = sorted(DADOS_EXTRAIDOS.rglob("finbra.csv"))

    if not csv_paths:
        print("Nenhum finbra.csv encontrado. Execute 01_extracao_dados.py primeiro.")
        sys.exit(1)

    frames = []
    for csv_path in csv_paths:
        ano = int(csv_path.parent.name)
        df_ano = ler_csv_finbra(csv_path, ano)
        n_capitais = df_ano["instituicao"].nunique()

        aviso = f"  <- ATENÇÃO: apenas {n_capitais}/26 capitais" if n_capitais < 26 else ""
        print(f"[{ano}] {len(df_ano):>6} linhas | {n_capitais:>2} capitais{aviso}")
        frames.append(df_ano)

    df = pd.concat(frames, ignore_index=True)
    print(f"\nTotal consolidado: {len(df):,} linhas x {len(df.columns)} colunas")

    df.to_parquet(SAIDA_PARQUET, index=False, engine="pyarrow")
    tamanho_mb = SAIDA_PARQUET.stat().st_size / 1_000_000
    print(f"Parquet salvo: {SAIDA_PARQUET.name}  ({tamanho_mb:.2f} MB)")

    return df


if __name__ == "__main__":
    consolidar()
