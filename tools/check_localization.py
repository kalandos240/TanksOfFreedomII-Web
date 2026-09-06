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
        # Upstream contains a few repeated keys. Godot effectively keeps one
        # mapping, so coverage intentionally compares the unique key set.
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
            # An intentionally blank English canonical value may be blank in
            # every locale. Non-empty English text must have non-empty text.
            if canonical[key].strip() and not values[key].strip():
                errors.append(f"BLANK {locale}: {stem}:{key}")

    return errors


def read_campaign_locale(path: Path, data: dict, locale: str):
    values = data.get(locale)
    if isinstance(values, dict):
        return values

    # Russian is maintained as a separate overlay so upstream campaign JSON
    # can be refreshed by bootstrap without overwriting translation work.
    if locale == "ru":
        overlay = path.with_name("translations.ru.json")
        if overlay.exists():
            values = json.loads(overlay.read_text(encoding="utf-8"))
            if isinstance(values, dict):
                return values
    return None


def check_campaign(path: Path, required: list[str]) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    if "en" not in data or not isinstance(data["en"], dict):
        return [f"NO ENGLISH CANONICAL BLOCK: {path.relative_to(ROOT)}"]

    canonical = data["en"]
    canonical_keys = set(canonical)
    label = path.parent.name

    for locale in required:
        values = read_campaign_locale(path, data, locale)
        if not isinstance(values, dict):
            errors.append(f"MISSING LANGUAGE {locale}: campaign:{label}")
            continue
        keys = set(values)
        for key in sorted(canonical_keys - keys):
            errors.append(f"MISSING {locale}: campaign:{label}:{key}")
        for key in sorted(keys - canonical_keys):
            errors.append(f"EXTRA {locale}: campaign:{label}:{key}")
        for key in sorted(canonical_keys & keys):
            canonical_value = canonical[key]
            value = values[key]
            canonical_has_text = isinstance(canonical_value, str) and bool(canonical_value.strip())
            if canonical_has_text and (not isinstance(value, str) or not value.strip()):
                errors.append(f"BLANK {locale}: campaign:{label}:{key}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Tanks of Freedom II translation coverage.")
    parser.add_argument(
        "--required",
        nargs="+",
        default=None,
        help="Backward-compatible locale list applied to both UI CSV and campaigns.",
    )
    parser.add_argument(
        "--required-csv",
        nargs="+",
        default=None,
        help="Locales required for common/core CSV files.",
    )
    parser.add_argument(
        "--required-campaigns",
        nargs="+",
        default=None,
        help="Locales required for campaign translations (RU may use translations.ru.json overlays).",
    )
    args = parser.parse_args()

    shared = args.required if args.required is not None else ["en", "pl"]
    csv_required = args.required_csv if args.required_csv is not None else shared
    campaign_required = args.required_campaigns if args.required_campaigns is not None else shared

    errors: list[str] = []
    for stem in ("common", "core"):
        errors.extend(check_csv_group(stem, csv_required))

    campaign_files = sorted(CAMPAIGNS.glob("*/translations.json"))
    if not campaign_files:
        errors.append("No campaign translations.json files found")

    ru_overlay_count = 0
    for path in campaign_files:
        errors.extend(check_campaign(path, campaign_required))

        # Every RU overlay that has been committed is considered complete work,
        # even while other campaigns are still awaiting translation. Validate it
        # strictly against the English canonical key set from day one.
        ru_overlay = path.with_name("translations.ru.json")
        if ru_overlay.exists():
            ru_overlay_count += 1
            if "ru" not in campaign_required:
                errors.extend(check_campaign(path, ["ru"]))

    if errors:
        print(f"Localization coverage FAILED: {len(errors)} issue(s)")
        for error in errors:
            print(error)
        return 1

    print("Localization coverage OK")
    print("Required UI locales:", ", ".join(csv_required))
    print("Required campaign locales:", ", ".join(campaign_required))
    print("Campaign translation files:", len(campaign_files))
    print("Strict Russian campaign overlays:", ru_overlay_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
