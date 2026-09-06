#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "assets" / "translations"
CAMPAIGNS = ROOT / "assets" / "campaigns"


def read_csv_keys(path: Path) -> tuple[list[str], dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or len(rows[0]) < 2 or rows[0][0] != "keys":
        raise RuntimeError(f"Invalid translation CSV header: {path}")
    locale = rows[0][1]
    values: dict[str, str] = {}
    for row in rows[1:]:
        if not row:
            continue
        key = row[0].strip()
        value = row[1] if len(row) > 1 else ""
        if not key:
            continue
        if key in values:
            raise RuntimeError(f"Duplicate key {key!r} in {path}")
        values[key] = value
    return [locale], values


def check_csv_group(stem: str, required: list[str]) -> list[str]:
    errors: list[str] = []
    canonical_path = TRANSLATIONS / f"{stem}.en.csv"
    _, canonical = read_csv_keys(canonical_path)
    canonical_keys = set(canonical)

    for locale in required:
        path = TRANSLATIONS / f"{stem}.{locale}.csv"
        if not path.exists():
            errors.append(f"MISSING FILE: {path.relative_to(ROOT)}")
            continue
        _, values = read_csv_keys(path)
        keys = set(values)
        for key in sorted(canonical_keys - keys):
            errors.append(f"MISSING {locale}: {stem}:{key}")
        for key in sorted(keys - canonical_keys):
            errors.append(f"EXTRA {locale}: {stem}:{key}")
        for key in sorted(canonical_keys & keys):
            if not values[key].strip():
                errors.append(f"BLANK {locale}: {stem}:{key}")

    return errors


def check_campaign(path: Path, required: list[str]) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    if "en" not in data or not isinstance(data["en"], dict):
        return [f"NO ENGLISH CANONICAL BLOCK: {path.relative_to(ROOT)}"]

    canonical = data["en"]
    canonical_keys = set(canonical)
    label = path.parent.name

    for locale in required:
        values = data.get(locale)
        if not isinstance(values, dict):
            errors.append(f"MISSING LANGUAGE {locale}: campaign:{label}")
            continue
        keys = set(values)
        for key in sorted(canonical_keys - keys):
            errors.append(f"MISSING {locale}: campaign:{label}:{key}")
        for key in sorted(keys - canonical_keys):
            errors.append(f"EXTRA {locale}: campaign:{label}:{key}")
        for key in sorted(canonical_keys & keys):
            value = values[key]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"BLANK {locale}: campaign:{label}:{key}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Tanks of Freedom II translation coverage.")
    parser.add_argument(
        "--required",
        nargs="+",
        default=["en", "pl"],
        help="Locales that must match the English canonical key set (for final portal build use: en pl ru).",
    )
    args = parser.parse_args()

    errors: list[str] = []
    for stem in ("common", "core"):
        errors.extend(check_csv_group(stem, args.required))

    campaign_files = sorted(CAMPAIGNS.glob("*/translations.json"))
    if not campaign_files:
        errors.append("No campaign translations.json files found")
    for path in campaign_files:
        errors.extend(check_campaign(path, args.required))

    if errors:
        print(f"Localization coverage FAILED: {len(errors)} issue(s)")
        for error in errors:
            print(error)
        return 1

    print("Localization coverage OK")
    print("Required locales:", ", ".join(args.required))
    print("Campaign translation files:", len(campaign_files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
