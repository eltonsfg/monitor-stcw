"""
Monitor STCW — Acordo Marítimo Bilateral Brasil-Portugal
Orquestrador principal: recolhe → filtra → guarda → notifica
"""
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone

# Carregar configuração
CONFIG = yaml.safe_load(
    (Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8")
)

def main():
    print(f"\n{'='*60}")
    print(f"  Monitor STCW — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")

    all_results = []
    dou_checked = False
    dre_checked = False

    # --- DOU (Brasil) ---
    if CONFIG["sources"]["dou"]["enabled"]:
        print("[1/2] Pesquisando DOU (Brasil)...")
        try:
            from scraper.sources import dou
            dou_items = dou.fetch()
            all_results.extend(dou_items)
            dou_checked = True
        except Exception as e:
            print(f"  [DOU] ERRO: {e}")

    # --- DRE (Portugal) ---
    if CONFIG["sources"]["dre"]["enabled"]:
        print("\n[2/2] Pesquisando DRE (Portugal)...")
        try:
            from scraper.sources import dre
            dre_items = dre.fetch()
            all_results.extend(dre_items)
            dre_checked = True
        except Exception as e:
            print(f"  [DRE] ERRO: {e}")

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
        # Só envia email para resultados novos (não duplicados)
        from storage.csv_sync import load_existing_urls
        # Os novos são os que foram efectivamente guardados agora
        new_only = all_results[:saved] if saved > 0 else []

        if new_only or not email_cfg.get("only_on_new_results", True):
            from notifier.email_alert import send_alert
            email_sent = send_alert(new_only or all_results, total_today=len(all_results))

    # --- Log diário ---
    append_log(log_path, {
        "dou_checked": dou_checked,
        "dre_checked": dre_checked,
        "new_results": saved,
        "total_results": len(all_results),
        "email_sent": email_sent,
    })

    print(f"\n{'='*60}")
    if saved > 0:
        print(f"  ✓ {saved} nova(s) publicação(ões) guardada(s) em '{csv_path}'")
        if email_sent:
            print(f"  ✓ Email de alerta enviado")
    else:
        print(f"  — Sem novas publicações hoje")
    print(f"{'='*60}\n")

    return 0 if True else 1


if __name__ == "__main__":
    sys.exit(main())
