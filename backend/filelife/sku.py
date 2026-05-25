"""
SKU generator and disassembler for MEMBRA FileLife Collateral Registry.

SKU format:
MBR-FIL-{CATEGORY}-{SUBCATEGORY}-{TYPE}-LC{STAGE}-V{VERSION:04d}-{JURISDICTION}-GH{REPOALIAS}-{COMMIT8}-SDV-{TX8}-KPI{PROFILE}-{COLLATERAL_FLAG}-{CHECKSUM}
"""
import hashlib


LIFECYCLE_LABELS = {
    0: "discovered",
    1: "registered",
    2: "raw hashed",
    3: "base64 encoded",
    4: "committed to GitHub",
    5: "anchored on-chain",
    6: "appraised",
    7: "verified",
    8: "amended/new version",
    9: "archived",
}

CATEGORY_LABELS = {
    "FIN": "Financial",
    "ACC": "Accounting",
    "INV": "Invoice",
    "REC": "Receipt",
    "BIL": "Bill",
    "TAX": "Tax",
    "CON": "Contract",
    "AUD": "Audit",
    "RPT": "Report",
    "STM": "Statement",
}

COLLATERAL_FLAG_LABELS = {
    "COL": "Collateral eligible",
    "NCL": "Not collateral eligible",
}


def _repo_alias(repo_alias: str) -> str:
    if not repo_alias or repo_alias == "NOREPO":
        return "NOREPO"
    return hashlib.sha256(repo_alias.encode()).hexdigest()[:5].upper()


def generate_sku(
    category: str,
    subcategory: str,
    kind: str,
    lifecycle_stage: int,
    version: int,
    jurisdiction: str,
    repo_alias: str,
    commit_short: str,
    tx_short: str,
    kpi_profile: int,
    collateral_flag: bool,
    raw_file_hash: str,
) -> str:
    """
    Generate a MEMBRA FileLife SKU.

    Returns the full SKU string.
    """
    cat = category.upper()[:3]
    subcat = subcategory.upper()[:3]
    knd = kind.upper()[:3]
    stage = max(0, min(9, lifecycle_stage))
    ver = max(1, version)
    jur = jurisdiction.upper()[:6]

    repo_part = _repo_alias(repo_alias)
    commit_part = (commit_short[:8].upper() if commit_short and commit_short != "00000000" else "00000000")
    tx_part = (tx_short[:8].upper() if tx_short and tx_short != "00000000" else "00000000")
    kpi = int(min(9, max(0, kpi_profile)))
    col_flag = "COL" if collateral_flag else "NCL"

    segments = [
        "MBR",
        "FIL",
        cat,
        subcat,
        knd,
        f"LC{stage}",
        f"V{ver:04d}",
        jur,
        f"GH{repo_part}",
        commit_part,
        "SDV",
        tx_part,
        f"KPI{kpi}",
        col_flag,
    ]

    base = "-".join(segments)
    checksum = hashlib.sha256(base.encode()).hexdigest()[:4].upper()
    return f"{base}-{checksum}"


def generate_sku_hash(sku: str) -> str:
    """sha256 of SKU string, returned as 'sha256:{hexdigest}'."""
    digest = hashlib.sha256(sku.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def validate_sku_checksum(sku: str) -> bool:
    """Validate the embedded 4-char checksum in a SKU."""
    try:
        parts = sku.split("-")
        if len(parts) < 15:
            return False
        checksum = parts[-1]
        base = "-".join(parts[:-1])
        expected = hashlib.sha256(base.encode()).hexdigest()[:4].upper()
        return checksum == expected
    except Exception:
        return False


def disassemble_sku(sku: str) -> dict:
    """
    Parse and disassemble a MEMBRA FileLife SKU into its semantic components.
    """
    parts = sku.split("-")
    valid = len(parts) == 15 and validate_sku_checksum(sku)

    if len(parts) < 15:
        return {
            "sku": sku,
            "valid": False,
            "error": f"Expected 15 segments, got {len(parts)}",
            "segments": {},
            "semantic_explanation": "Invalid SKU format.",
            "privacy_explanation": "No raw file contents, personal identity, or confidential data is embedded in this SKU.",
            "github_reference": "N/A",
            "solana_reference": "N/A",
            "lifecycle_meaning": "Unknown",
            "collateral_meaning": "Unknown",
        }

    (namespace, obj_type, category, subcategory, kind,
     lifecycle_raw, version_raw, jurisdiction,
     gh_alias_raw, commit_short, network, tx_short,
     kpi_raw, collateral_flag, checksum) = parts

    # Parse lifecycle
    lc_num = int(lifecycle_raw.replace("LC", "")) if lifecycle_raw.startswith("LC") else -1
    lc_label = LIFECYCLE_LABELS.get(lc_num, "unknown")

    # Parse version
    ver_num = int(version_raw.replace("V", "")) if version_raw.startswith("V") else 0

    # Parse GH alias
    gh_alias = gh_alias_raw.replace("GH", "", 1)

    # Parse KPI profile
    kpi_num = int(kpi_raw.replace("KPI", "")) if kpi_raw.startswith("KPI") else 0

    # Category label
    cat_label = CATEGORY_LABELS.get(category, category)
    col_meaning = COLLATERAL_FLAG_LABELS.get(collateral_flag, collateral_flag)

    semantic = (
        f"This is a MEMBRA {cat_label} ({subcategory}) {kind} file record, "
        f"at lifecycle stage {lc_num} ({lc_label}), version {ver_num}, "
        f"jurisdiction {jurisdiction}. "
        f"GitHub repo alias: {gh_alias}, last commit: {commit_short}. "
        f"Solana Devnet anchor tx alias: {tx_short}. "
        f"KPI profile: {kpi_num}. Collateral status: {col_meaning}."
    )

    github_ref = f"Commit {commit_short} in GitHub repo alias {gh_alias}"
    solana_ref = f"Transaction alias {tx_short} on Solana Devnet"

    lifecycle_meaning = (
        f"Stage {lc_num}: {lc_label.capitalize()}. "
        + {
            0: "File discovered, not yet registered.",
            1: "File registered in the MEMBRA registry.",
            2: "Raw file hash computed and stored.",
            3: "File base64-encoded and hash computed.",
            4: "Manifest committed to GitHub version control.",
            5: "Hashes anchored on the Solana blockchain.",
            6: "File appraised by LLM-based appraisal engine.",
            7: "All hashes verified and integrity confirmed.",
            8: "File amended; new version created.",
            9: "File archived; no longer active.",
        }.get(lc_num, "Unknown stage.")
    )

    return {
        "sku": sku,
        "valid": valid,
        "checksum_valid": validate_sku_checksum(sku),
        "segments": {
            "namespace": {"value": namespace, "meaning": "MEMBRA registry namespace"},
            "object_type": {"value": obj_type, "meaning": "File object"},
            "category": {"value": category, "meaning": f"Category: {cat_label}"},
            "subcategory": {"value": subcategory, "meaning": f"Subcategory: {subcategory}"},
            "kind": {"value": kind, "meaning": f"Document kind: {kind}"},
            "lifecycle": {"value": lifecycle_raw, "meaning": f"Stage {lc_num}: {lc_label}"},
            "version": {"value": version_raw, "meaning": f"Version {ver_num}"},
            "jurisdiction": {"value": jurisdiction, "meaning": f"Legal jurisdiction: {jurisdiction}"},
            "github_alias": {"value": gh_alias_raw, "meaning": f"GitHub repo fingerprint alias: {gh_alias}"},
            "commit_short": {"value": commit_short, "meaning": f"Last GitHub commit (first 8 chars): {commit_short}"},
            "network": {"value": network, "meaning": "Solana Devnet blockchain network"},
            "tx_short": {"value": tx_short, "meaning": f"Solana anchor transaction alias: {tx_short}"},
            "kpi_profile": {"value": kpi_raw, "meaning": f"Collateral KPI profile score: {kpi_num}/9"},
            "collateral_flag": {"value": collateral_flag, "meaning": col_meaning},
            "checksum": {"value": checksum, "meaning": "4-char SHA256 integrity checksum of all segments"},
        },
        "semantic_explanation": semantic,
        "privacy_explanation": (
            "No raw file contents, personal identity, email, SSN, or confidential data "
            "is embedded in this SKU. All identifiers are cryptographic hashes or aliases."
        ),
        "github_reference": github_ref,
        "solana_reference": solana_ref,
        "lifecycle_meaning": lifecycle_meaning,
        "collateral_meaning": col_meaning,
    }
