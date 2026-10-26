"""Read public release metadata; installation always remains a user action."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, Request, build_opener

import truststore

from app_version import RELEASES_URL, VERSION

LATEST_RELEASE_API = "https://api.github.com/repos/SamuelMeyer1/loan-inventory-releases/releases/latest"
MAX_METADATA_BYTES = 1024 * 1024


@dataclass(frozen=True)
class Release:
    version: str
    download_url: str
    notes: str


@dataclass(frozen=True)
class UpdateCheck:
    latest_version: str | None
    available: Release | None = None


def version_numbers(version: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"\d{1,5}\.\d{1,5}\.\d{1,5}", version, flags=re.ASCII):
        raise ValueError("Versionsnumret måste ha formatet 1.18.0.")
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def check_for_updates(current_version: str = VERSION) -> UpdateCheck:
    current = version_numbers(current_version)
    request = Request(LATEST_RELEASE_API, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"LoanInventory/{current_version}",
    })
    try:
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with build_opener(HTTPSHandler(context=context)).open(request, timeout=10) as response:
            content = response.read(MAX_METADATA_BYTES + 1)
    except HTTPError as error:
        error.close()
        if error.code == 404:
            return UpdateCheck(None)
        raise ValueError(f"GitHub svarade med HTTP {error.code}. Försök igen senare.") from error
    except URLError as error:
        if isinstance(error.reason, ssl.SSLCertVerificationError):
            raise ValueError(
                "GitHubs HTTPS-certifikat kunde inte verifieras med datorns certifikatlagring. "
                "Kontrollera datorns datum och betrodda certifikat med IT. "
                "Certifikatkontrollen är fortfarande påslagen. "
                "Du kan prova Versionssida i webbläsaren utan att kringgå säkerhetsvarningar."
            ) from error
        raise
    if len(content) > MAX_METADATA_BYTES:
        raise ValueError("Versionsinformationen från GitHub är för stor.")
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("GitHub returnerade ogiltig versionsinformation.")
    published_at = data.get("published_at")
    if (data.get("draft") is not False or data.get("prerelease") is not False
            or not isinstance(published_at, str) or not published_at):
        raise ValueError("Versionen är inte en publicerad stabil release.")
    tag = data.get("tag_name")
    if not isinstance(tag, str):
        raise ValueError("Releasen saknar en giltig versionstagg.")
    version = tag.removeprefix("v")
    if version_numbers(version) <= current:
        return UpdateCheck(version)
    assets = data.get("assets")
    filename = f"LoanInventory-{version}-Setup.exe"
    if not isinstance(assets, list):
        raise ValueError("Releasen saknar installationsfiler.")
    matches = [asset for asset in assets if isinstance(asset, dict) and asset.get("name") == filename]
    if len(matches) != 1:
        raise ValueError(f"Releasen måste innehålla exakt en {filename}.")
    asset = matches[0]
    expected_url = f"{RELEASES_URL}/download/{tag}/{filename}"
    if asset.get("browser_download_url") != expected_url or asset.get("state") != "uploaded":
        raise ValueError("Installationsfilens adress eller publiceringsstatus är ogiltig.")
    size = asset.get("size")
    if type(size) is not int or not 0 < size <= 512 * 1024 * 1024:
        raise ValueError("Installationsfilens storlek är ogiltig.")
    notes = data.get("body")
    if notes is None:
        notes = ""
    if not isinstance(notes, str):
        raise ValueError("Versionsbeskrivningen har fel format.")
    return UpdateCheck(version, Release(version, expected_url, notes[:800]))
