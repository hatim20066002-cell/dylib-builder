import os
import time
import uuid
import requests
import logging
from config import GITHUB_USERNAME, GITHUB_REPO, GITHUB_TOKEN, BUILD_TIMEOUT, BUILD_POLL_INTERVAL

logger = logging.getLogger(__name__)

BASE_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


def upload_file_to_github(local_path: str, filename: str) -> str | None:
    """
    Upload a file to GitHub repo releases as an asset,
    returns the download URL.
    We'll use the raw upload-to-repo approach via the Contents API.
    """
    import base64

    with open(local_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode()

    remote_path = f"uploads/{uuid.uuid4().hex}/{filename}"
    url = f"{BASE_URL}/contents/{remote_path}"

    resp = requests.put(url, headers=HEADERS, json={
        "message": f"Upload {filename}",
        "content": content
    })

    if resp.status_code not in (200, 201):
        logger.error(f"Upload failed: {resp.text}")
        return None

    download_url = resp.json()["content"]["download_url"]
    return download_url, remote_path


def delete_github_file(remote_path: str, sha: str):
    """Delete a file from the GitHub repo (cleanup after build)."""
    url = f"{BASE_URL}/contents/{remote_path}"
    requests.delete(url, headers=HEADERS, json={
        "message": f"Cleanup {remote_path}",
        "sha": sha
    })


def get_file_sha(remote_path: str) -> str | None:
    url = f"{BASE_URL}/contents/{remote_path}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json().get("sha")
    return None


def trigger_build(archive_url: str, language: str, output_name: str, job_id: str) -> str | None:
    """
    Trigger the GitHub Actions workflow.
    Returns the run ID if successful.
    """
    url = f"{BASE_URL}/actions/workflows/build_dylib.yml/dispatches"
    payload = {
        "ref": "main",
        "inputs": {
            "archive_url": archive_url,
            "language": language,
            "output_name": output_name,
            "job_id": job_id
        }
    }

    resp = requests.post(url, headers=HEADERS, json=payload)
    if resp.status_code != 204:
        logger.error(f"Failed to trigger workflow: {resp.text}")
        return None

    # Wait a moment then find the run ID
    time.sleep(5)
    return _get_latest_run_id(job_id)


def _get_latest_run_id(job_id: str) -> str | None:
    """Find the workflow run that was just triggered."""
    url = f"{BASE_URL}/actions/runs?event=workflow_dispatch&per_page=5"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        return None

    runs = resp.json().get("workflow_runs", [])
    for run in runs:
        if run.get("status") in ("queued", "in_progress"):
            return str(run["id"])

    # Fallback: return the most recent run
    if runs:
        return str(runs[0]["id"])
    return None


def wait_for_build(run_id: str) -> tuple[bool, str]:
    """
    Poll GitHub Actions until the build finishes.
    Returns (success, conclusion).
    """
    url = f"{BASE_URL}/actions/runs/{run_id}"
    elapsed = 0

    while elapsed < BUILD_TIMEOUT:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            return False, "API error"

        data = resp.json()
        status = data.get("status")
        conclusion = data.get("conclusion")

        if status == "completed":
            return conclusion == "success", conclusion or "unknown"

        time.sleep(BUILD_POLL_INTERVAL)
        elapsed += BUILD_POLL_INTERVAL

    return False, "timeout"


def download_artifact(run_id: str, job_id: str, output_path: str) -> bool:
    """
    Download the compiled .dylib artifact from GitHub Actions.
    """
    # List artifacts for this run
    url = f"{BASE_URL}/actions/runs/{run_id}/artifacts"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        return False

    artifacts = resp.json().get("artifacts", [])
    target_artifact = None
    for art in artifacts:
        if f"dylib-output-{job_id}" in art["name"]:
            target_artifact = art
            break

    if not target_artifact:
        logger.error(f"Artifact not found for job_id={job_id}")
        return False

    # Download the artifact zip
    download_url = target_artifact["archive_download_url"]
    resp = requests.get(download_url, headers=HEADERS, stream=True)
    if resp.status_code != 200:
        return False

    zip_path = output_path + ".zip"
    with open(zip_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    # Extract dylib from zip
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(os.path.dirname(output_path))

    os.remove(zip_path)

    # Find the .dylib file
    out_dir = os.path.dirname(output_path)
    for f in os.listdir(out_dir):
        if f.endswith('.dylib'):
            found = os.path.join(out_dir, f)
            if found != output_path:
                os.rename(found, output_path)
            return True

    return os.path.exists(output_path)
