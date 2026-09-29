from datetime import date, datetime, time, timedelta, timezone


FUSO_HORARIO_PLANOS = timezone(timedelta(hours=-3))
HORARIO_INICIO_PLANOS = time(8, 0)


def horario_inicio_plano(data: date | datetime) -> datetime:
    """Mantem o dia da agenda local e fixa o inicio em 08:00."""
    if isinstance(data, datetime):
        if data.tzinfo is not None:
            data = data.astimezone(FUSO_HORARIO_PLANOS)
        data = data.date()
    return datetime.combine(data, HORARIO_INICIO_PLANOS)
