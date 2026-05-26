"""SMTP 邮件发送。"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from .fetcher import Paper
from .render import render_html, render_plain


def send_email(
    papers: list[Paper],
    config: dict,
    date: datetime,
    dry_run: bool = False,
):
    """发送 HTML 邮件摘要。"""
    if dry_run:
        print("[dry-run] 跳过邮件发送")
        smtp = config.get("email", {})
        receiver = smtp.get("receiver") or "（未配置邮箱）"
        print(f"[dry-run] 将发送 {len(papers)} 篇论文到 {receiver}")
        # 打印纯文本预览
        print("\n--- 邮件预览 ---")
        print(render_plain(papers, date))
        return

    smtp = config["email"]
    html_body = render_html(papers, date)
    plain_body = render_plain(papers, date)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{smtp['subject_prefix']} {date.strftime('%Y-%m-%d')} · {len(papers)} papers"
    msg["From"] = smtp["sender"]
    msg["To"] = smtp["receiver"]

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(smtp["smtp_server"], smtp["port"]) as server:
        server.login(smtp["sender"], smtp["password"])
        server.send_message(msg)

    print(f"邮件已发送: {smtp['sender']} -> {smtp['receiver']}")
