"""
Notificação por email via SMTP (Gmail ou outro).
Configuração via variáveis de ambiente:
  EMAIL_FROM      ex: seuemail@gmail.com
  EMAIL_PASSWORD  app password do Gmail (não a senha principal)
  EMAIL_TO        destinatário (pode ser o mesmo)
  EMAIL_SMTP      opcional, default: smtp.gmail.com
  EMAIL_PORT      opcional, default: 587
"""
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_alert(new_results: list[dict], total_today: int = 0) -> bool:
    """
    Envia email com os novos resultados encontrados.
    Devolve True se enviado com sucesso.
    """
    from_addr = os.environ.get("EMAIL_FROM", "")
    password = os.environ.get("EMAIL_PASSWORD", "")
    to_addr = os.environ.get("EMAIL_TO", from_addr)
    smtp_host = os.environ.get("EMAIL_SMTP", "smtp.gmail.com")
    smtp_port = int(os.environ.get("EMAIL_PORT", "587"))

    if not from_addr or not password:
        print("  [Email] EMAIL_FROM ou EMAIL_PASSWORD não configurados — email ignorado")
        return False

    subject, body_html, body_text = _build_message(new_results, total_today)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(from_addr, password)
            server.sendmail(from_addr, to_addr, msg.as_string())
        print(f"  [Email] Alerta enviado para {to_addr}")
        return True
    except Exception as e:
        print(f"  [Email] ERRO ao enviar: {e}")
        return False


def _build_message(results: list[dict], total_today: int) -> tuple[str, str, str]:
    date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    count = len(results)

    subject = f"[STCW Monitor] ⚠️ {count} nova(s) publicação(ões) encontrada(s) — {date_str}"

    # Texto simples
    lines = [
        f"ALERTA — Monitor STCW Brasil-Portugal",
        f"Data: {date_str}",
        f"Novas publicações encontradas: {count}",
        "",
    ]
    for i, r in enumerate(results, 1):
        lines += [
            f"--- Resultado {i} ---",
            f"Fonte:     {r['source']} ({r['country']})",
            f"Título:    {r['title']}",
            f"Data:      {r['date_found']}",
            f"Keywords:  {r['matched_keywords']}",
            f"URL:       {r['url']}",
            f"Resumo:    {r.get('description', '')}",
            "",
        ]
    body_text = "\n".join(lines)

    # HTML
    rows_html = ""
    for r in results:
        rows_html += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee">
            <strong>{r['source']}</strong> <span style="color:#888">({r['country']})</span>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee">
            <a href="{r['url']}" style="color:#1a73e8">{r['title']}</a><br>
            <small style="color:#555">{r.get('description', '')[:200]}</small>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px;color:#444">
            {r['matched_keywords']}
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px;white-space:nowrap">
            {r['date_found']}
          </td>
        </tr>"""

    body_html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:900px;margin:0 auto">
      <h2 style="color:#c0392b">⚓ Monitor STCW — Acordo Marítimo Brasil-Portugal</h2>
      <p style="color:#555">
        <strong>{count} nova(s) publicação(ões)</strong> encontrada(s) em <strong>{date_str}</strong>
      </p>
      <table width="100%" cellspacing="0" style="border-collapse:collapse;font-size:14px">
        <thead>
          <tr style="background:#f5f5f5">
            <th align="left" style="padding:8px">Fonte</th>
            <th align="left" style="padding:8px">Publicação</th>
            <th align="left" style="padding:8px">Keywords</th>
            <th align="left" style="padding:8px">Data</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      <hr style="margin-top:30px;border:none;border-top:1px solid #eee">
      <p style="font-size:12px;color:#aaa">
        Monitor automático — DOU (Brasil) + DRE (Portugal)<br>
        Autoridades: DPC · DGRM
      </p>
    </body></html>"""

    return subject, body_html, body_text
