"""
Filtros de relevância para publicações do DOU e DRE.
"""
import re
import yaml
from pathlib import Path

_config = None

def _get_config():
    global _config
    if _config is None:
        _config = yaml.safe_load(
            (Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8")
        )
    return _config


def _normalise(text: str) -> str:
    """Remove acentos e converte para minúsculas para comparação."""
    replacements = {
        "á": "a", "à": "a", "â": "a", "ã": "a",
        "é": "e", "ê": "e", "í": "i", "ó": "o",
        "ô": "o", "õ": "o", "ú": "u", "ç": "c",
    }
    text = text.lower()
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def get_all_keywords() -> list[str]:
    cfg = _get_config()
    kw = cfg.get("keywords", {})
    all_kw = []
    for group in kw.values():
        all_kw.extend(group)
    return all_kw


def get_matched_keywords(text: str) -> list[str]:
    """Devolve a lista de keywords encontradas no texto."""
    norm = _normalise(text)
    matched = []
    for kw in get_all_keywords():
        if _normalise(kw) in norm:
            matched.append(kw)
    return matched


def _has_any_from_group(text_norm: str, group_name: str) -> bool:
    cfg = _get_config()
    group = cfg.get("keywords", {}).get(group_name, [])
    return any(_normalise(kw) in text_norm for kw in group)


def _has_country_pair(text_norm: str) -> bool:
    """Verifica se o texto menciona ambos os países."""
    has_brazil = any(t in text_norm for t in ["brasil", "brasileira", "brasileiros"])
    has_portugal = any(t in text_norm for t in ["portugal", "portuguesa", "portugues"])
    return has_brazil and has_portugal


# Palavras de desambiguação: se estas aparecem, o texto NÃO é marítimo
_DPC_EXCLUSIONS = [
    "autoridade tributária", "divisão de planeamento", "divisão de coordenação",
    "finanças", "tributária", "aduaneira", "concursal", "procedimento concursal",
    "recursos humanos", "ministério da", "secretaria de estado",
]

# Contexto marítimo obrigatório quando a única keyword é "DPC" ou "ANTAQ"
_MARITIME_CONTEXT = [
    "maritim", "marítim", "portos", "costas", "aquaviar", "gente do mar",
    "stcw", "certificad", "endoss", "habilitac", "habilitaç", "naval",
    "capitania", "tripulant", "nautico", "náutico",
]


def _is_ambiguous_authority(kw_norm: str, text_norm: str) -> bool:
    """
    Retorna True se a keyword é uma sigla ambígua (DPC, ANTAQ) e o texto
    parece ser de outro domínio (não marítimo).
    """
    ambiguous = ["dpc", "antaq"]
    if kw_norm not in ambiguous:
        return False
    # Se encontrar exclusão explícita → falso positivo
    if any(excl in text_norm for excl in _DPC_EXCLUSIONS):
        return True
    # Se não houver nenhum contexto marítimo → ambíguo, rejeitar
    if not any(ctx in text_norm for ctx in _MARITIME_CONTEXT):
        return True
    return False


def is_relevant(title: str, description: str = "") -> tuple[bool, list[str]]:
    """
    Verifica se a publicação é relevante para o monitoramento STCW.
    Devolve (relevante: bool, keywords_encontradas: list).
    """
    cfg = _get_config()
    rules = cfg.get("match_rules", {})
    text = f"{title} {description}"
    text_norm = _normalise(text)

    matched = get_matched_keywords(text)
    if not matched:
        return False, []

    # Filtrar keywords ambíguas sem contexto marítimo
    matched = [kw for kw in matched if not _is_ambiguous_authority(_normalise(kw), text_norm)]
    if not matched:
        return False, []

    # Verifica regra: tem de ter pelo menos um termo dos grupos obrigatórios
    required_groups = rules.get("require_any_of_groups", ["primary", "authorities"])
    has_required = any(_has_any_from_group(text_norm, g) for g in required_groups)
    if not has_required:
        return False, []

    # Verifica regra: tem de mencionar o par de países
    if rules.get("require_country_pair", True):
        if not _has_country_pair(text_norm):
            # Excepção: keywords muito específicas dispensam o par de países
            bypass_keywords = ["stcw", "dgrm", "endosso de certificado",
                               "certificacao maritima", "reconhecimento mutuo"]
            if not any(b in text_norm for b in bypass_keywords):
                return False, []

    return True, matched
