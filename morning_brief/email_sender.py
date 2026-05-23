"""Render the digest as HTML and send via SMTP."""
from __future__ import annotations

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Config
from .core import Entry

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_html(cfg: Config, entries: list[Entry]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    tmpl = env.get_template("email.html.j2")
    return tmpl.render(
        topic_name=cfg.topic.name,
        tagline=cfg.email.tagline,
        footer=cfg.email.footer,
        date_human=datetime.now().strftime("%A, %B %d, %Y"),
        entries=entries,
    )


def send(cfg: Config, plain_text: str, entries: list[Entry]) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    subject = cfg.email.subject.format(topic_name=cfg.topic.name, date=today)

    html = render_html(cfg, entries)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.env.email_sender
    msg["To"] = cfg.env.email_recipient
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(cfg.env.smtp_server, cfg.env.smtp_port, timeout=30) as s:
        s.starttls()
        s.login(cfg.env.email_sender, cfg.env.email_app_password)
        s.send_message(msg)
