#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
from pathlib import Path

FETCH_LOADER = '''\t\t<script data-tof-compressed-loader="1">
(function () {
    "use strict";
    const nativeFetch = window.fetch.bind(window);
    const packedFiles = new Map([
        ["index.wasm", "index.wasmz"],
        ["index.pck", "index.pckz"],
    ]);

    window.fetch = async function (input, init) {
        let requestUrl;
        if (typeof input === "string" || input instanceof URL) {
            requestUrl = new URL(input, window.location.href);
        } else if (input instanceof Request) {
            requestUrl = new URL(input.url, window.location.href);
        } else {
            return nativeFetch(input, init);
        }

        if (requestUrl.origin !== window.location.origin) {
            return nativeFetch(input, init);
        }

        const requestedName = requestUrl.pathname.split("/").pop();
        const packedName = packedFiles.get(requestedName);
        if (!packedName) {
            return nativeFetch(input, init);
        }

        if (typeof DecompressionStream === "undefined") {
            throw new Error("This browser does not support the gzip decompression required by this Web build.");
        }

        const packedUrl = new URL(packedName, requestUrl);
        let packedRequest = packedUrl.href;
        if (input instanceof Request) {
            packedRequest = new Request(packedUrl.href, input);
        }
        const response = await nativeFetch(packedRequest, init);
        if (!response.ok || !response.body) {
            throw new Error("Failed loading compressed game file '" + packedName + "'.");
        }

        const headers = new Headers(response.headers);
        headers.delete("content-encoding");
        headers.delete("content-length");
        headers.set("content-type", requestedName.endsWith(".wasm") ? "application/wasm" : "application/octet-stream");

        return new Response(response.body.pipeThrough(new DecompressionStream("gzip")), {
            status: response.status,
            statusText: response.statusText,
            headers: headers,
        });
    };
})();
\t\t</script>
'''


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gzip_file(src: Path, dst: Path) -> tuple[int, int, str]:
    original_hash = sha256(src)
    with src.open("rb") as source, dst.open("wb") as raw_out:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_out, compresslevel=9, mtime=0) as compressed:
            shutil.copyfileobj(source, compressed, length=1024 * 1024)

    roundtrip_hash = hashlib.sha256()
    with gzip.open(dst, "rb") as check:
        for chunk in iter(lambda: check.read(1024 * 1024), b""):
            roundtrip_hash.update(chunk)
    if roundtrip_hash.hexdigest() != original_hash:
        raise RuntimeError(f"gzip round-trip hash mismatch for {src.name}")

    return src.stat().st_size, dst.stat().st_size, original_hash


def inject_loader(html_path: Path) -> None:
    html = html_path.read_text(encoding="utf-8")
    if 'data-tof-compressed-loader="1"' in html:
        return

    marker = '<script src="index.js"></script>'
    marker_pos = html.find(marker)
    if marker_pos < 0:
        raise RuntimeError("Godot index.js script marker not found in exported HTML")

    line_start = html.rfind("\n", 0, marker_pos) + 1
    html = html[:line_start] + FETCH_LOADER + html[line_start:]
    html_path.write_text(html, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package the Godot Web export for the Yandex Games 100 MB unpacked limit."
    )
    parser.add_argument("web_dir", nargs="?", default="build/web")
    args = parser.parse_args()

    root = Path(args.web_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)

    html = root / "index.html"
    if not html.is_file():
        raise FileNotFoundError(html)

    pairs = [
        (root / "index.wasm", root / "index.wasmz"),
        (root / "index.pck", root / "index.pckz"),
    ]

    for src, dst in pairs:
        if not src.is_file():
            raise FileNotFoundError(src)
        original_size, packed_size, digest = gzip_file(src, dst)
        print(f"{src.name}: {original_size} -> {packed_size} bytes; sha256={digest}")

    inject_loader(html)

    # Remove unpacked payloads only after both gzip round-trip checks and HTML
    # injection have succeeded. The Godot loader still requests index.wasm and
    # index.pck; the injected fetch shim transparently serves the packed files.
    for src, _ in pairs:
        src.unlink()

    required = [html, root / "index.js", root / "index.wasmz", root / "index.pckz"]
    for path in required:
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"Missing packaged Web file: {path.name}")

    final_html = html.read_text(encoding="utf-8")
    for needle in (
        "DecompressionStream",
        "index.wasmz",
        "index.pckz",
        '<script src="/sdk.js"></script>',
        "LoadingAPI",
    ):
        if needle not in final_html:
            raise RuntimeError(f"Packaged HTML validation failed: {needle}")

    total = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    print(f"Packaged unpacked file bytes: {total}")
    if total > 100_000_000:
        raise RuntimeError(f"Yandex Games unpacked size limit exceeded: {total} > 100000000")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
