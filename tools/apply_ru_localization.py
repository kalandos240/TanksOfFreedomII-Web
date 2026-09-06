#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        raise FileNotFoundError(f"Required file is missing: {path}")
    return target.read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Patch anchor not found for {label}")
    return text.replace(old, new, 1)


def patch_project_translation_resources() -> None:
    path = "project.godot"
    text = read(path)

    old_intl = (
        'locale/translations=PackedStringArray("res://assets/translations/common.en.en.translation", '
        '"res://assets/translations/common.pl.pl.translation", '
        '"res://assets/translations/core.en.en.translation", '
        '"res://assets/translations/core.pl.pl.translation")'
    )
    new_intl = (
        'locale/translations=PackedStringArray("res://assets/translations/common.en.en.translation", '
        '"res://assets/translations/common.pl.pl.translation", '
        '"res://assets/translations/common.ru.ru.translation", '
        '"res://assets/translations/core.en.en.translation", '
        '"res://assets/translations/core.pl.pl.translation", '
        '"res://assets/translations/core.ru.ru.translation")'
    )
    text = replace_once(text, old_intl, new_intl, "internationalization RU resources")

    old_locale = (
        'translations=PackedStringArray("res://assets/translations/core.en.en.translation", '
        '"res://assets/translations/core.pl.pl.translation", '
        '"res://assets/translations/common.en.en.translation", '
        '"res://assets/translations/common.pl.pl.translation")'
    )
    new_locale = (
        'translations=PackedStringArray("res://assets/translations/core.en.en.translation", '
        '"res://assets/translations/core.pl.pl.translation", '
        '"res://assets/translations/core.ru.ru.translation", '
        '"res://assets/translations/common.en.en.translation", '
        '"res://assets/translations/common.pl.pl.translation", '
        '"res://assets/translations/common.ru.ru.translation")'
    )
    text = replace_once(text, old_locale, new_locale, "locale RU resources")
    write(path, text)


def patch_language_selector_values() -> None:
    path = "scenes/ui/menu/settings/settings_general.tscn"
    text = read(path)
    text = replace_once(
        text,
        'available_values = ["en", "pl"]',
        'available_values = ["en", "pl", "ru"]',
        "Russian language selector value",
    )
    write(path, text)


def patch_language_selector_labels() -> None:
    path = "scenes/ui/menu/settings/setting_option_rotating.gd"
    text = read(path)

    old = '''\tfor known_value in self.available_values:
\t\tif value == known_value:
\t\t\tif known_value is String:
\t\t\t\tself.button_label.set_text(known_value)
\t\t\telse:
\t\t\t\tself.button_label.set_text(str(known_value))
\t\t\treturn
'''
    new = '''\tfor known_value in self.available_values:
\t\tif value == known_value:
\t\t\tif self.option_key == "locale":
\t\t\t\tvar language_names = {"en": "English", "pl": "Polski", "ru": "Русский"}
\t\t\t\tself.button_label.set_text(language_names.get(str(known_value), str(known_value)))
\t\t\telif known_value is String:
\t\t\t\tself.button_label.set_text(known_value)
\t\t\telse:
\t\t\t\tself.button_label.set_text(str(known_value))
\t\t\treturn
'''
    text = replace_once(text, old, new, "native language names")
    write(path, text)


def patch_settings_first_run_marker() -> None:
    path = "scripts/services/settings.gd"
    text = read(path)
    text = replace_once(
        text,
        '\t"locale": "en",\n',
        '\t"locale": "en",\n\t"platform_locale_initialized": false,\n',
        "platform locale initialization marker",
    )
    write(path, text)


def patch_yandex_language_policy() -> None:
    path = "scripts/services/yandex.gd"
    text = read(path)
    text = text.replace(
        "# Russian is intentionally enabled only after the complete RU translation lands.\n",
        "# Platform language is used only on the first launch; manual selection persists.\n",
        1,
    )
    text = replace_once(
        text,
        'const SUPPORTED_AUTO_LOCALES := ["en", "pl"]',
        'const SUPPORTED_AUTO_LOCALES := ["en", "pl", "ru"]',
        "Yandex Russian auto locale",
    )

    old = '''func _apply_platform_language() -> void:
\tvar locale = self.platform_language.to_lower()
\tif locale.contains("-"):
\t\tlocale = locale.get_slice("-", 0)
\tif locale.contains("_"):
\t\tlocale = locale.get_slice("_", 0)

\tif not SUPPORTED_AUTO_LOCALES.has(locale):
\t\tlocale = "en"

\tSettings.set_option("locale", locale)
'''
    new = '''func _apply_platform_language() -> void:
\t# Do not overwrite a language the player selected on a previous launch.
\tif bool(Settings.get_option("platform_locale_initialized")):
\t\treturn

\tvar locale = self.platform_language.to_lower()
\tif locale.contains("-"):
\t\tlocale = locale.get_slice("-", 0)
\tif locale.contains("_"):
\t\tlocale = locale.get_slice("_", 0)

\tif not SUPPORTED_AUTO_LOCALES.has(locale):
\t\tlocale = "en"

\tSettings.set_option("locale", locale)
\tSettings.set_option("platform_locale_initialized", true)
'''
    text = replace_once(text, old, new, "first-launch Yandex locale policy")
    write(path, text)


def patch_campaign_ru_overlay_loader() -> None:
    path = "scripts/services/campaign.gd"
    text = read(path)

    old = '''func _load_translations(directory_path):
\tif self.filesystem.file_exists(directory_path + "/translations.json"):
\t\tvar translations = self.filesystem.read_json_from_file(directory_path + "/translations.json")

\t\tfor locale in translations:
\t\t\tvar position = Translation.new()
\t\t\tposition.locale = locale

\t\t\tfor key in translations[locale]:
\t\t\t\tposition.add_message(key, translations[locale][key])
\t\t\tTranslationServer.add_translation(position)
'''
    new = '''func _load_translations(directory_path):
\tif self.filesystem.file_exists(directory_path + "/translations.json"):
\t\tvar translations = self.filesystem.read_json_from_file(directory_path + "/translations.json")

\t\tfor locale in translations:
\t\t\tvar position = Translation.new()
\t\t\tposition.locale = locale

\t\t\tfor key in translations[locale]:
\t\t\t\tposition.add_message(key, translations[locale][key])
\t\t\tTranslationServer.add_translation(position)

\t# Keep Russian text in a Web-port overlay so upstream campaign JSON can be
\t# refreshed without overwriting the translation work.
\tvar ru_overlay_path = directory_path + "/translations.ru.json"
\tif self.filesystem.file_exists(ru_overlay_path):
\t\tvar ru_messages = self.filesystem.read_json_from_file(ru_overlay_path)
\t\tvar ru_translation = Translation.new()
\t\tru_translation.locale = "ru"
\t\tfor key in ru_messages:
\t\t\tru_translation.add_message(key, ru_messages[key])
\t\tTranslationServer.add_translation(ru_translation)
'''
    text = replace_once(text, old, new, "campaign Russian overlay loader")
    write(path, text)


def main() -> None:
    patch_project_translation_resources()
    patch_language_selector_values()
    patch_language_selector_labels()
    patch_settings_first_run_marker()
    patch_yandex_language_policy()
    patch_campaign_ru_overlay_loader()
    print("Applied Russian localization runtime integration.")


if __name__ == "__main__":
    main()
