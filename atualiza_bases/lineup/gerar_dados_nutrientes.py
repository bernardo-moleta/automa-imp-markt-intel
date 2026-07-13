"""
gerar_dados_nutrientes.py
==========================
Le as bases BI_Importacao_Siacesp.xlsx e BI_Line_Up_ORION.xlsx, agrega os
dados necessarios para o relatorio comparativo de pontos nutricionais
(N, P, K) entre SIACESP e ORION, e exporta um arquivo JavaScript
(dados_nutrientes.js) consumido pela nova aba do dashboard_comparativo.html.

Uso:
    python gerar_dados_nutrientes.py

Gera:
    dados_nutrientes.js
"""

import json
import pandas as pd

SIACESP_PATH = "BI_Importacao_Siacesp.xlsx"
ORION_PATH = "BI_Line_Up_ORION.xlsx"
OUTPUT_PATH = "dados_nutrientes.js"


def carregar_siacesp(path):
    df = pd.read_excel(path)

    df["Z_PERÍODO"] = pd.to_datetime(df["Z_PERÍODO"], errors="coerce")
    for col in ["VOLUME", "N", "P2O5", "K20"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df.dropna(subset=["Z_PERÍODO"])
    df["ym"] = df["Z_PERÍODO"].dt.strftime("%Y-%m")

    agg = df.groupby(["ym", "PORTO", "Y_PRODUTO PARA"], as_index=False)[
        ["VOLUME", "N", "P2O5", "K20"]
    ].sum()

    # remove linhas totalmente zeradas para reduzir o tamanho do arquivo
    agg = agg[(agg["VOLUME"] != 0) | (agg["N"] != 0) | (agg["P2O5"] != 0) | (agg["K20"] != 0)]

    registros = [
        {
            "ym": r["ym"],
            "porto": r["PORTO"],
            "produto": r["Y_PRODUTO PARA"],
            "volume": round(float(r["VOLUME"]), 2),
            "n": round(float(r["N"]), 2),
            "p": round(float(r["P2O5"]), 2),
            "k": round(float(r["K20"]), 2),
        }
        for _, r in agg.iterrows()
    ]
    return registros


def carregar_orion(path):
    df = pd.read_excel(path)

    df["Z_ETB"] = pd.to_datetime(df["Z_ETB"], errors="coerce", format="mixed", dayfirst=False)
    df["Z_DATA_POSIÇÃO"] = pd.to_datetime(df["Z_DATA_POSIÇÃO"], errors="coerce")
    df["Qtty"] = pd.to_numeric(df["Qtty"], errors="coerce").fillna(0)

    df = df.dropna(subset=["Z_ETB", "Z_DATA_POSIÇÃO"])
    df["etbYm"] = df["Z_ETB"].dt.strftime("%Y-%m")
    df["pos"] = df["Z_DATA_POSIÇÃO"].dt.strftime("%Y-%m-%d")

    agg = df.groupby(["pos", "etbYm", "Port", "Y_PRODUTO PARA"], as_index=False)["Qtty"].sum()
    agg = agg[agg["Qtty"] != 0]

    registros = [
        {
            "pos": r["pos"],
            "etbYm": r["etbYm"],
            "porto": (r["Port"] or "").strip() if isinstance(r["Port"], str) else r["Port"],
            "produto": r["Y_PRODUTO PARA"],
            "qtty": round(float(r["Qtty"]), 2),
        }
        for _, r in agg.iterrows()
    ]
    return registros


def montar_meta(siacesp, orion):
    siacesp_yms = sorted({r["ym"] for r in siacesp})
    siacesp_portos = sorted({r["porto"] for r in siacesp if r["porto"]})
    siacesp_produtos = sorted({r["produto"] for r in siacesp if r["produto"]})

    orion_pos = sorted({r["pos"] for r in orion})
    orion_yms = sorted({r["etbYm"] for r in orion})
    orion_portos = sorted({r["porto"] for r in orion if r["porto"]})
    orion_produtos = sorted({r["produto"] for r in orion if r["produto"]})

    ultima_posicao = orion_pos[-1] if orion_pos else None
    # Padrão de negócio: mês anterior + mês da posição mais recente
    # (ex.: posição 2026-07-09 -> período de análise Junho/Julho)
    if ultima_posicao:
        ano_pos, mes_pos = map(int, ultima_posicao[:7].split("-"))
        mes_de = mes_pos - 1 if mes_pos > 1 else 12
        ano_de = ano_pos if mes_pos > 1 else ano_pos - 1
        orion_de_padrao = f"{ano_de:04d}-{mes_de:02d}"
        orion_ate_padrao = f"{ano_pos:04d}-{mes_pos:02d}"
    else:
        orion_de_padrao = None
        orion_ate_padrao = None

    return {
        "siacesp_periodos": siacesp_yms,
        "siacesp_portos": siacesp_portos,
        "siacesp_produtos": siacesp_produtos,
        "siacesp_de_padrao": siacesp_yms[-5] if len(siacesp_yms) >= 5 else (siacesp_yms[0] if siacesp_yms else None),
        "siacesp_ate_padrao": siacesp_yms[-1] if siacesp_yms else None,
        "orion_posicoes": orion_pos,
        "orion_periodos": orion_yms,
        "orion_portos": orion_portos,
        "orion_produtos": orion_produtos,
        "orion_posicao_padrao": ultima_posicao,
        "orion_de_padrao": orion_de_padrao,
        "orion_ate_padrao": orion_ate_padrao,
    }


def main():
    print("Lendo SIACESP...")
    siacesp = carregar_siacesp(SIACESP_PATH)
    print(f"  {len(siacesp)} linhas agregadas")

    print("Lendo ORION...")
    orion = carregar_orion(ORION_PATH)
    print(f"  {len(orion)} linhas agregadas")

    meta = montar_meta(siacesp, orion)

    dados = {
        "siacesp": siacesp,
        "orion": orion,
        "meta": meta,
        "coeficientes_orion": {
            "SAM": 0.21,
            "UREA": 0.46,
            "MAP": 0.52,
            "NP": 0.42,
            "SSP": 0.20,
            "TSP": 0.45,
            "MOP": 0.60,
        },
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("const nutrientesData = " + json.dumps(dados, ensure_ascii=False) + ";\n")

    print(f"✅ Arquivo '{OUTPUT_PATH}' gerado com sucesso!")
    print(f"   Período SIACESP padrão: {meta['siacesp_de_padrao']} a {meta['siacesp_ate_padrao']}")
    print(f"   ORION posição padrão: {meta['orion_posicao_padrao']} | período: {meta['orion_de_padrao']} a {meta['orion_ate_padrao']}")


if __name__ == "__main__":
    main()