"""
Armazenamento em CSV — resultados e log diário.
"""
import csv
import os
from datetime import datetime, timezone
from pathlib import Path

RESULTS_FIELDS = ["date_found", "source", "country", "title", "matched_keywords", "url", "description"]
LOG_FIELDS = ["date", "dou_checked", "dre_checked", "new_results", "total_results", "email_sent"]


def load_existing_urls(csv_path: str) -> set[str]:
    """Carrega URLs já guardados para deduplicação."""
    path = Path(csv_path)
    if not path.exists():
        return set()
    seen = set()
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("url"):
                seen.add(row["url"])
    return seen


def save_results(csv_path: str, new_items: list[dict]) -> int:
    """
    Guarda novos resultados no CSV.
    Devolve o número de itens efectivamente guardados (excluindo duplicados).
    """
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_urls = load_existing_urls(csv_path)
    to_save = [item for item in new_items if item.get("url") not in existing_urls]

    if not to_save:
        return 0

    write_header = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTS_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(to_save)

    return len(to_save)


def append_log(log_path: str, stats: dict):
    """Regista o resultado da execução diária (incluindo dias sem resultados)."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    write_header = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow({
            "date": datetime.now(timezone.utc).date().isoformat(),
            **stats,
        })
