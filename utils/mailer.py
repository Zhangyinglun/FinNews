"""SMTP mailer utilities (Gmail-friendly)."""

from __future__ import annotations

import base64
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional


class GmailSmtpMailer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send_html(
        self,
        *,
        subject: str,
        html_body: str,
        email_from: str,
        to_list: List[str],
        images: Optional[Dict[str, str]] = None,
    ):
        """
        发送HTML邮件 (支持内嵌图片)

        Args:
            subject: 邮件标题
            html_body: HTML正文
            email_from: 发件人
            to_list: 收件人列表
            images: 内嵌图片字典 {content_id: base64_data}
        """
        if not to_list:
            raise ValueError("to_list cannot be empty")

        # 如果有图片，使用 multipart/related 结构
        if images:
            msg = MIMEMultipart("related")
            msg_alt = MIMEMultipart("alternative")
            msg.attach(msg_alt)
        else:
            msg = MIMEMultipart("alternative")
            msg_alt = msg

        msg["Subject"] = subject
        msg["From"] = email_from
        msg["To"] = ", ".join(to_list)

        # 构建纯文本版本
        plain_body = "".join(
            line.rstrip() + "\n"
            for line in html_body.replace("<br>", "\n").splitlines()
        ).strip()

        # 添加正文部分
        msg_alt.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg_alt.attach(MIMEText(html_body, "html", "utf-8"))

        # 添加内嵌图片
        if images:
            for cid, b64_data in images.items():
                try:
                    # 解码 Base64
                    img_data = base64.b64decode(b64_data)
                    img = MIMEImage(img_data)

                    # 设置 Content-ID (必须包含尖括号)
                    img.add_header("Content-ID", f"<{cid}>")
                    img.add_header(
                        "Content-Disposition", "inline", filename=f"{cid}.png"
                    )

                    msg.attach(img)
                except Exception as e:
                    print(f"⚠️ 无法附加图片 {cid}: {e}")

        with smtplib.SMTP(self.host, self.port, timeout=30) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(email_from, to_list, msg.as_string())

    def send_plain(
        self,
        *,
        subject: str,
        plain_body: str,
        email_from: str,
        to_list: List[str],
    ):
        """
        发送纯文本邮件（适用于 ASCII 艺术字符格式）

        Args:
            subject: 邮件标题
            plain_body: 纯文本正文
            email_from: 发件人
            to_list: 收件人列表
        """
        if not to_list:
            raise ValueError("to_list cannot be empty")

        msg = MIMEText(plain_body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = email_from
        msg["To"] = ", ".join(to_list)

        with smtplib.SMTP(self.host, self.port, timeout=30) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(email_from, to_list, msg.as_string())
