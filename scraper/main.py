"""
Monitor STCW — Acordo Marítimo Bilateral Brasil-Portugal
Orquestrador principal: recolhe → filtra → guarda → notifica
"""
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone

# Carregar configuração
CONFIG = yaml.safe_load(
    (Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8")
)

# Quando DISABLE_BR_SOURCES=true (GitHub Actions), desactivar fontes brasileiras
# Railway (São Paulo) trata das fontes BR com IP local
_DISABLE_BR = os.environ.get("DISABLE_BR_SOURCES", "").lower() == "true"
if _DISABLE_BR:
    for src in ("dou", "dpc", "ciaga"):
        if src in CONFIG["sources"]:
            CONFIG["sources"][src]["enabled"] = False

def main():
    print(f"\n{'='*60}")
    print(f"  Monitor STCW — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")

    all_results = []
    sources_checked = {}

    # --- DOU (Brasil) ---
    if CONFIG["sources"]["dou"]["enabled"]:
        print("[1/5] Pesquisando DOU (Brasil)...")
        try:
            from scraper.sources import dou
            items = dou.fetch()
            all_results.extend(items)
            sources_checked["dou"] = True
        except Exception as e:
            print(f"  [DOU] ERRO: {e}")
            sources_checked["dou"] = False

    # --- DRE (Portugal) ---
    if CONFIG["sources"]["dre"]["enabled"]:
        print("\n[2/5] Pesquisando DRE (Portugal)...")
        try:
            from scraper.sources import dre
            items = dre.fetch()
            all_results.extend(items)
            sources_checked["dre"] = True
        except Exception as e:
            print(f"  [DRE] ERRO: {e}")
            sources_checked["dre"] = False

    # --- DPC (Brasil) ---
    if CONFIG["sources"].get("dpc", {}).get("enabled", False):
        print("\n[3/5] Pesquisando DPC — Diretoria de Portos e Costas (Brasil)...")
        try:
            from scraper.sources import dpc
            items = dpc.fetch()
            all_results.extend(items)
            sources_checked["dpc"] = True
        except Exception as e:
            print(f"  [DPC] ERRO: {e}")
            sources_checked["dpc"] = False

    # --- CIAGA (Brasil) ---
    if CONFIG["sources"].get("ciaga", {}).get("enabled", False):
        print("\n[4/5] Pesquisando CIAGA — Centro de Instrução (Brasil)...")
        try:
            from scraper.sources import ciaga
            items = ciaga.fetch()
            all_results.extend(items)
            sources_checked["ciaga"] = True
        except Exception as e:
            print(f"  [CIAGA] ERRO: {e}")
            sources_checked["ciaga"] = False

    # --- DGRM (Portugal) ---
    if CONFIG["sources"].get("dgrm", {}).get("enabled", False):
        print("\n[5/5] Pesquisando DGRM — Direção-Geral de Recursos Marítimos (Portugal)...")
        try:
            from scraper.sources import dgrm
            items = dgrm.fetch()
            all_results.extend(items)
            sources_checked["dgrm"] = True
        except Exception as e:
            print(f"  [DGRM] ERRO: {e}")
            sources_checked["dgrm"] = False

    print(f"\nTotal encontrado: {len(all_results)} publicação(ões) relevante(s)")

    # --- Guardar em CSV ---
    from storage.csv_sync import save_results, append_log

    csv_path = CONFIG["storage"]["csv_file"]
    log_path = CONFIG["storage"]["log_file"]

    saved = save_results(csv_path, all_results)
    print(f"Novas no CSV: {saved} (duplicados ignorados: {len(all_results) - saved})")

    # --- Notificação por email ---
    email_sent = False
    email_cfg = CONFIG.get("email", {})

    if email_cfg.get("enabled") and all_results:
        new_only = all_results[:saved] if saved > 0 else []
        if new_only or not email_cfg.get("only_on_new_results", True):
            from notifier.email_alert import send_alert
            email_sent = send_alert(new_only or all_results, total_today=len(all_results))

    # --- Log diário ---
    append_log(log_path, {
        **{f"{k}_checked": v for k, v in sources_checked.items()},
        # compatibilidade retroactiva
        "dou_checked": sources_checked.get("dou", False),
        "dre_checked": sources_checked.get("dre", False),
        "new_results": saved,
        "total_results": len(all_results),
        "email_sent": email_sent,
    })

    print(f"\n{'='*60}")
    checked_list = ", ".join(k.upper() for k, v in sources_checked.items() if v)
    print(f"  Fontes verificadas: {checked_list or '-'}")
    if saved > 0:
        print(f"  [OK] {saved} nova(s) publicacao(oes) guardada(s) em '{csv_path}'")
        if email_sent:
            print(f"  [OK] Email de alerta enviado")
    else:
        print(f"  [-] Sem novas publicacoes hoje")
    print(f"{'='*60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
