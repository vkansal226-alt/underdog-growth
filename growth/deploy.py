"""Cross-repo push to the storefront (walnut) + wait for Vercel to serve the new asset."""
import subprocess
import time
import urllib.request
import urllib.error


def push_walnut(web_dir, message):
    """Commit + push the walnut checkout. Returns True if anything was pushed."""
    def git(*a):
        return subprocess.run(["git", "-C", web_dir, *a], check=True)

    git("add", "-A")
    staged = subprocess.run(["git", "-C", web_dir, "diff", "--cached", "--quiet"])
    if staged.returncode == 0:
        return False  # nothing to commit
    git("-c", "user.name=design-bot",
        "-c", "user.email=design-bot@users.noreply.github.com",
        "commit", "-m", message)
    git("push", "origin", "HEAD")
    return True


def wait_for_url(url, timeout=300, interval=10):
    """Poll a URL until it returns HTTP 200 (Vercel finished deploying), or timeout."""
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
