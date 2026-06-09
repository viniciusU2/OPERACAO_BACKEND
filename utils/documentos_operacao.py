import re
import unicodedata


def limpar_texto(valor):
    texto = str(valor or "").strip().upper()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(char for char in texto if unicodedata.category(char) != "Mn")


def parte_codigo(valor):
    texto = limpar_texto(valor)
    texto = re.sub(r"[^A-Z0-9]+", "_", texto)
    return texto.strip("_")


def abreviar_tipo_ativo(nome):
    normalizado = limpar_texto(nome)

    if not normalizado:
        return ""
    if "GMG" in normalizado:
        return "GMG"
    if "GRUPO" in normalizado and "GERADOR" in normalizado:
        return "GMG"
    if "GERADOR" in normalizado:
        return "GMG"
    if "PARA" in normalizado and "RAIO" in normalizado:
        return "PR"
    if "SECCION" in normalizado:
        return "SEC"
    if "DISJUNT" in normalizado:
        return "DJ"
    if "TC" in normalizado or "CORRENTE" in normalizado:
        return "TC"
    if "TP" in normalizado or "POTENCIAL" in normalizado:
        return "TP"
    if "REATOR" in normalizado:
        return "RC"
    if "TRANSFORMADOR" in normalizado or "TRAFO" in normalizado:
        return "TR"
    if "BARRA" in normalizado:
        return "BR"
    if "TORRE" in normalizado:
        return "TOR"

    palavras = re.findall(r"[A-Z0-9]+", normalizado)
    if len(palavras) == 1:
        return palavras[0][:4]
    return "".join(palavra[0] for palavra in palavras)[:4]


def formatar_classe_tensao(valor):
    if valor is None:
        return ""

    numero = float(valor)
    if numero.is_integer():
        return f"{int(numero)}K"

    return f"{numero:.2f}".rstrip("0").rstrip(".") + "K"


def especie_documento_por_ativo(ativo):
    tipo_ativo = getattr(ativo, "tipo_ativo", None)
    abreviacao = abreviar_tipo_ativo(getattr(tipo_ativo, "nome", None))
    classe_tensao = formatar_classe_tensao(getattr(ativo, "tensao_nominal_kv", None))
    fabricante = parte_codigo(getattr(ativo, "fabricante", None))

    if abreviacao and classe_tensao and fabricante:
        return "_".join([abreviacao, classe_tensao, fabricante])

    return ""


def normalizar_prioridade_operacao(prioridade):
    if prioridade == "ALTA":
        return "NIVEL_1"
    if prioridade == "MEDIA":
        return "NIVEL_3"
    if prioridade == "BAIXA":
        return "NIVEL_5"
    return prioridade or "NIVEL_3"
