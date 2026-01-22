#!/usr/bin/env python3
"""
使用 GitHub API 触发 workflow
需要 GitHub Personal Access Token
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def get_github_token():
    """获取 GitHub token"""
    # 尝试从环境变量获取
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    # 尝试从 git credential helper 获取
    try:
        result = subprocess.run(
            ["git", "config", "--get", "credential.helper"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print("🔐 检测到 git credential helper")
            print("💡 尝试从 git 凭据获取 token...")

            # 获取远程 URL
            remote_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            )
            remote_url = remote_result.stdout.strip()

            # 解析仓库信息
            if "github.com" in remote_url:
                # 尝试从凭据助手获取
                cred_input = f"protocol=https\nhost=github.com\n\n"
                cred_result = subprocess.run(
                    ["git", "credential", "fill"],
                    input=cred_input,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if cred_result.returncode == 0:
                    for line in cred_result.stdout.split("\n"):
                        if line.startswith("password="):
                            return line.split("=", 1)[1].strip()

    except Exception as e:
        print(f"⚠️  无法自动获取 token: {e}")

    return None


def trigger_workflow(
    token, repo_owner, repo_name, workflow_name="finnews-schedule.yml"
):
    """触发 GitHub Actions workflow"""
    import urllib.request
    import urllib.error

    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_name}/dispatches"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "FinNews-Trigger-Script",
    }

    data = json.dumps({"ref": "main"}).encode("utf-8")

    try:
        req = urllib.request.Request(api_url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                return True, "Workflow 触发成功"
            else:
                return False, f"意外的响应状态: {response.status}"

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_data = json.loads(error_body)
            error_message = error_data.get("message", error_body)
        except:
            error_message = error_body

        return False, f"HTTP {e.code}: {error_message}"

    except urllib.error.URLError as e:
        return False, f"网络错误: {e.reason}"

    except Exception as e:
        return False, f"未知错误: {e}"


def main():
    print("🚀 准备触发 finnews-schedule workflow...")
    print("")

    # 获取仓库信息
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote_url = result.stdout.strip()

        # 解析 owner/repo
        import re

        match = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)", remote_url)
        if not match:
            print("❌ 无法解析仓库信息")
            sys.exit(1)

        repo_owner = match.group(1)
        repo_name = match.group(2)

        print(f"📦 仓库: {repo_owner}/{repo_name}")

    except Exception as e:
        print(f"❌ 获取仓库信息失败: {e}")
        sys.exit(1)

    # 显示当前提交
    try:
        sha_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_sha = sha_result.stdout.strip()

        msg_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_message = msg_result.stdout.strip().split("\n")[0]

        print(f"📍 当前提交: {current_sha}")
        print(f"   消息: {current_message}")
        print("")

        if "BOM" in current_message or current_sha == "8f67bdf":
            print("✅ 当前提交包含 BOM 修复")
        else:
            print("⚠️  警告: 当前提交可能不包含 BOM 修复")

        print("")

    except Exception as e:
        print(f"⚠️  无法获取提交信息: {e}")

    # 获取 token
    print("🔐 获取 GitHub token...")
    token = get_github_token()

    if not token:
        print("")
        print("❌ 无法自动获取 GitHub token")
        print("")
        print("请手动设置环境变量:")
        print("  export GITHUB_TOKEN=your_token")
        print("")
        print("或访问网页端手动触发:")
        print(f"  https://github.com/{repo_owner}/{repo_name}/actions")
        print("")
        print("获取 token: https://github.com/settings/tokens")
        print("需要权限: repo, workflow")
        sys.exit(1)

    print(f"✅ 已获取 token (前 4 位: {token[:4]}...)")
    print("")

    # 触发 workflow
    print("🚀 触发 workflow...")
    success, message = trigger_workflow(token, repo_owner, repo_name)

    print("")
    if success:
        print("✅ " + message)
        print("")
        print("💡 查看运行状态:")
        print(f"  https://github.com/{repo_owner}/{repo_name}/actions")
        print("")
        print("⏳ 请等待几秒钟，然后刷新页面查看新的运行记录")
        sys.exit(0)
    else:
        print("❌ 触发失败: " + message)
        print("")
        print("💡 你可以:")
        print("  1. 检查 token 权限 (需要 repo + workflow)")
        print("  2. 手动访问网页端触发:")
        print(f"     https://github.com/{repo_owner}/{repo_name}/actions")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)
