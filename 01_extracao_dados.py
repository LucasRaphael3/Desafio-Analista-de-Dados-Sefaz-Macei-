import zipfile
from pathlib import Path

DADOS_COMPACTOS = Path(__file__).parent / "dados_compactos"
DADOS_EXTRAIDOS = Path(__file__).parent / "dados_extraidos"


def extrair_zips() -> None:
    zips = sorted(DADOS_COMPACTOS.rglob("*.zip"))

    if not zips:
        print(f"Nenhum .zip encontrado em: {DADOS_COMPACTOS}")
        return

    for zip_path in zips:
        # O nome da pasta pai identifica o ano do exercício (ex.: dados_compactos/2022/)
        ano = zip_path.parent.name
        destino = DADOS_EXTRAIDOS / ano
        destino.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            membros = zf.namelist()
            zf.extractall(destino)

        print(f"[{ano}] {zip_path.name} -> {destino}/ ({len(membros)} arquivo(s))")

    print(f"\nExtração concluída. Arquivos disponíveis em: {DADOS_EXTRAIDOS}")


if __name__ == "__main__":
    extrair_zips()
