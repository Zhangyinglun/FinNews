"""
测试 Gmail SMTP 发送功能（mock 版）
"""

import pytest
from unittest.mock import MagicMock

from utils.mailer import GmailSmtpMailer


@pytest.fixture
def mock_smtp(monkeypatch):
    """mock smtplib.SMTP，避免真实网络连接"""
    mock_server = MagicMock()
    mock_server.__enter__ = MagicMock(return_value=mock_server)
    mock_server.__exit__ = MagicMock(return_value=False)

    smtp_ctor = MagicMock(return_value=mock_server)
    monkeypatch.setattr("utils.mailer.smtplib.SMTP", smtp_ctor)
    return smtp_ctor, mock_server


@pytest.fixture
def mailer():
    return GmailSmtpMailer(
        host="smtp.gmail.com",
        port=587,
        username="test@gmail.com",
        password="test_password",
        use_tls=True,
    )


def test_send_html_calls_smtp(mock_smtp, mailer):
    """send_html 应建立 SMTP 连接并发送邮件"""
    smtp_ctor, _ = mock_smtp
    mailer.send_html(
        subject="FinNews Test",
        html_body="<html><body><p>Test email</p></body></html>",
        email_from="test@gmail.com",
        to_list=["recipient@example.com"],
    )

    # 验证 SMTP 构造时使用了正确参数
    smtp_ctor.assert_called_once_with("smtp.gmail.com", 587, timeout=30)


def test_send_html_calls_sendmail(mock_smtp, mailer):
    """send_html 应调用 sendmail 发送邮件"""
    _, mock_server = mock_smtp
    mailer.send_html(
        subject="FinNews Test",
        html_body="<html><body><p>Test email</p></body></html>",
        email_from="test@gmail.com",
        to_list=["recipient@example.com"],
    )

    # 验证 sendmail 被调用
    mock_server.sendmail.assert_called_once()
    call_args = mock_server.sendmail.call_args
    from_addr = call_args[0][0]
    to_addrs = call_args[0][1]
    assert from_addr == "test@gmail.com"
    assert "recipient@example.com" in to_addrs


def test_send_html_multiple_recipients(mock_smtp, mailer):
    """send_html 应支持多个收件人"""
    _, mock_server = mock_smtp
    recipients = ["user1@example.com", "user2@example.com"]
    mailer.send_html(
        subject="Bulk Test",
        html_body="<html><body><p>Test</p></body></html>",
        email_from="test@gmail.com",
        to_list=recipients,
    )

    call_args = mock_server.sendmail.call_args
    to_addrs = call_args[0][1]
    for r in recipients:
        assert r in to_addrs
