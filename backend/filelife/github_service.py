"""Real GitHub REST API integration for MEMBRA FileLife."""
import base64
import hashlib
import json
import os
from typing import List, Optional

import httpx
from fastapi import HTTPException

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "overandor/membramoney-protocol")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    if not GITHUB_TOKEN:
        raise HTTPException(503, "GITHUB_TOKEN not configured. Set the GITHUB_TOKEN environment variable.")
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def generate_repo_alias(repo: str) -> str:
    return "GH" + hashlib.sha256(repo.encode()).hexdigest()[:5].upper()


async def get_repo_info(repo: Optional[str] = None) -> dict:
    r = repo or GITHUB_REPO
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{GITHUB_API}/repos/{r}", headers=_headers())
        if resp.status_code != 200:
            raise HTTPException(502, f"GitHub API error: {resp.status_code} {resp.text[:200]}")
        d = resp.json()
        return {"name": d["full_name"], "url": d["html_url"], "default_branch": d["default_branch"]}


async def commit_manifest(sku: str, manifest: dict, repo: Optional[str] = None, branch: Optional[str] = None) -> dict:
    r = repo or GITHUB_REPO
    b = branch or GITHUB_BRANCH
    file_path = f"filelife-manifests/{sku}.json"
    content_b64 = base64.b64encode(json.dumps(manifest, indent=2).encode()).decode()

    async with httpx.AsyncClient(timeout=20) as client:
        # Check if file already exists to get its SHA for update
        existing_sha = None
        get_resp = await client.get(
            f"{GITHUB_API}/repos/{r}/contents/{file_path}",
            headers=_headers(),
            params={"ref": b},
        )
        if get_resp.status_code == 200:
            existing_sha = get_resp.json().get("sha")

        body: dict = {
            "message": f"feat(filelife): register manifest for {sku}",
            "content": content_b64,
            "branch": b,
        }
        if existing_sha:
            body["sha"] = existing_sha

        put_resp = await client.put(
            f"{GITHUB_API}/repos/{r}/contents/{file_path}",
            headers=_headers(),
            json=body,
        )
        if put_resp.status_code not in (200, 201):
            raise HTTPException(502, f"GitHub commit failed: {put_resp.status_code} {put_resp.text[:300]}")

        data = put_resp.json()
        commit_sha = data["commit"]["sha"]
        repo_alias = generate_repo_alias(r)
        return {
            "repo_alias": repo_alias,
            "repo": r,
            "branch": b,
            "commit_sha": commit_sha,
            "commit_short": commit_sha[:8].upper(),
            "commit_url": data["commit"]["html_url"],
        }


async def get_file_history(sku: str, repo: Optional[str] = None) -> List[dict]:
    r = repo or GITHUB_REPO
    file_path = f"filelife-manifests/{sku}.json"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GITHUB_API}/repos/{r}/commits",
            headers=_headers(),
            params={"path": file_path, "per_page": 20},
        )
        if resp.status_code != 200:
            return []
        commits = resp.json()
        return [
            {
                "sha": c["sha"],
                "short_sha": c["sha"][:8].upper(),
                "message": c["commit"]["message"],
                "date": c["commit"]["committer"]["date"],
                "url": c["html_url"],
            }
            for c in commits
        ]
