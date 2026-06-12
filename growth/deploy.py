"""Deploy a new design to the live storefront (Vercel) + persist it to the vault.

The storefront (projects/underdog-goods-web inside the private `walnut` vault) is
deployed to Vercel via the Vercel CLI, not git-push. So we:
  1. deploy_vercel(web_dir)        -> `vercel deploy --prod` (token in cloud, local auth on the Mac)
  2. wait_for_url(url)             -> confirm the new asset is actually live before posting
  3. persist_to_vault(...)         -> commit the new product back to the vault for the next cycle
"""
import os
import subprocess
import time
import urllib.request
import urllib.error


def deploy_vercel(web_dir):
    """`vercel deploy --prod` from the storefront dir. Uses VERCEL_TOKEN +
    VERCEL_ORG_ID/VERCEL_PROJECT_ID env when set (cloud, headless); falls back to
    the locally-authenticated CLI + the dir's .vercel link otherwise. Returns
    (ok, production_url|None)."""
    cmd = ["vercel", "deploy", "--prod", "--yes"]
    if os.environ.get("VERCEL_TOKEN"):
        cmd += ["--token", os.environ["VERCEL_TOKEN"]]
    try:
        r = subprocess.run(cmd, cwd=web_dir, capture_output=True, text=True, timeout=900)
    except Exception as e:
        print(f"  vercel deploy failed to launch: {e}")
        return False, None
    out = (r.stdout or "") + (r.stderr or "")
    print(out[-600:])
    # vercel prints the deployment URL on stdout
    url = next((ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip().startswith("https://")), None)
    return r.returncode == 0, url


def wait_for_url(url, timeout=300, interval=10):
    """Poll a URL until HTTP 200 (production domain finished updating), or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 200:
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 200:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def persist_to_vault(vault_dir, paths, message):
    """Commit + push ONLY the given storefront paths to the vault (keeps the next
    cycle's clone in sync). No-op when vault_dir is unset (e.g. local verify runs)."""
    if not vault_dir:
        return False

    def git(*a):
        return subprocess.run(["git", "-C", vault_dir, *a], check=True)

    git("add", *paths)
    if subprocess.run(["git", "-C", vault_dir, "diff", "--cached", "--quiet"]).returncode == 0:
        return False
    git("-c", "user.name=design-bot",
        "-c", "user.email=design-bot@users.noreply.github.com",
        "commit", "-m", message)
    git("push", "origin", "HEAD")
    return True
