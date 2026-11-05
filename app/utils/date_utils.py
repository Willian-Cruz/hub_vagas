"""Conversão das datas de publicação que os portais exibem nos cards."""
import re
from datetime import date, datetime, time, timedelta
from typing import Optional

_DATA_BR = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
_HA_DIAS = re.compile(r"\bh[aá]\s+(\d+)\s+dias?\b", re.IGNORECASE)
_HA_HORAS = re.compile(r"\bh[aá]\s+(\d+)\s+(?:horas?|minutos?)\b", re.IGNORECASE)


def parse_data_vagas(texto, referencia: Optional[date] = None) -> Optional[datetime]:
    """Converte a data do card do Vagas.com em datetime (precisão de dia).

    Formatos vistos no portal: "Há 4 dias" e "21/10/2026". Também trata
    "Há 3 horas", "Hoje" e "Ontem". Formato desconhecido devolve None.

    `referencia` é a data da coleta (padrão: hoje); existe para os testes.
    """
    if not texto:
        return None
    ref = referencia or date.today()
    limpo = " ".join(str(texto).split())

    data_br = _DATA_BR.search(limpo)
    if data_br:
        dia, mes, ano = (int(parte) for parte in data_br.groups())
        try:
            return datetime(ano, mes, dia)
        except ValueError:
            return None

    ha_dias = _HA_DIAS.search(limpo)
    if ha_dias:
        return datetime.combine(ref - timedelta(days=int(ha_dias.group(1))), time.min)

    if _HA_HORAS.search(limpo):
        return datetime.combine(ref, time.min)

    minusculo = limpo.casefold()
    if "hoje" in minusculo:
        return datetime.combine(ref, time.min)
    if "ontem" in minusculo:
        return datetime.combine(ref - timedelta(days=1), time.min)
    return None


def parse_data_infojobs(valor) -> Optional[datetime]:
    """Converte o atributo `data-value` do InfoJobs ("2026/10/30 10:59:00")."""
    if not valor:
        return None
    texto = str(valor).strip()
    for formato in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None
