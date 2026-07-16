#!/usr/bin/env bash
# Lädt WoltLab Suite Core nach ./woltlab/
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
load_env

ZIP_PATH=""
ZIP_URL=""
FORCE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --zip) ZIP_PATH="$2"; shift 2 ;;
        --zip-url) ZIP_URL="$2"; shift 2 ;;
        --force) FORCE=1; shift ;;
        *) die "Unbekanntes Argument: $1" ;;
    esac
done

mkdir -p "$ROOT/woltlab" "$ROOT/var"

if [[ -f "$ROOT/woltlab/install.php" && "$FORCE" != "1" ]]; then
    msg "✓ WoltLab-Dateien bereits vorhanden (überspringe Download)." \
        "✓ WoltLab files already present (skipping download)."
    exit 0
fi

# Leeren wenn force oder unvollständig
if [[ "$FORCE" == "1" ]] || [[ ! -f "$ROOT/woltlab/install.php" ]]; then
    find "$ROOT/woltlab" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true
fi

TMP_ZIP="$ROOT/var/woltlab-suite-${WSC_VERSION}.zip"

if [[ -n "$ZIP_PATH" ]]; then
    [[ -f "$ZIP_PATH" ]] || die "ZIP nicht gefunden: $ZIP_PATH"
    cp -f "$ZIP_PATH" "$TMP_ZIP"
elif [[ -n "$ZIP_URL" ]]; then
    msg "↓ Lade $ZIP_URL …" "↓ Downloading $ZIP_URL …"
    if [[ "${WSC_QUIET:-0}" == "1" ]]; then curl -fsSL -o "$TMP_ZIP" "$ZIP_URL"; else curl -fL --progress-bar -o "$TMP_ZIP" "$ZIP_URL"; fi
else
    URL="https://assets.woltlab.com/release/woltlab-suite-${WSC_VERSION}.zip"
    msg "↓ Lade WoltLab Suite Core ${WSC_VERSION}…" "↓ Downloading WoltLab Suite Core ${WSC_VERSION}…"
    if [[ "${WSC_QUIET:-0}" == "1" ]]; then curl -fsSL -o "$TMP_ZIP" "$URL"; else curl -fL --progress-bar -o "$TMP_ZIP" "$URL"; fi
    if [[ -n "${WSC_SHA256:-}" ]]; then
        echo "${WSC_SHA256}  ${TMP_ZIP}" | sha256sum -c - >/dev/null \
            || die "SHA-256 stimmt nicht (Datei beschädigt oder falsche Version)."
    fi
fi

msg "⇢ Entpacken nach ./woltlab/ …" "⇢ Extracting to ./woltlab/ …"
# ZIP kann upload/ oder Root-Dateien enthalten
TMP_DIR="$ROOT/var/extract-$$"
mkdir -p "$TMP_DIR"
unzip -q "$TMP_ZIP" -d "$TMP_DIR"

if [[ -d "$TMP_DIR/upload" ]]; then
    cp -r "$TMP_DIR/upload/." "$ROOT/woltlab/"
elif [[ -f "$TMP_DIR/install.php" ]]; then
    cp -r "$TMP_DIR/." "$ROOT/woltlab/"
else
    # ein Unterordner?
    sub=$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n1)
    if [[ -n "$sub" && -f "$sub/install.php" ]]; then
        cp -r "$sub/." "$ROOT/woltlab/"
    else
        rm -rf "$TMP_DIR"
        die "Unerwartete ZIP-Struktur (kein install.php)."
    fi
fi
rm -rf "$TMP_DIR"

[[ -f "$ROOT/woltlab/install.php" ]] || die "Nach Entpacken fehlt install.php."

# Apache = www-data; zugleich a+rwX damit Host-Skripte schreiben können
if docker info >/dev/null 2>&1; then
    docker run --rm -v "$ROOT/woltlab:/var/www/html" php:8.3-apache-bookworm \
        bash -c 'chown -R www-data:www-data /var/www/html && chmod -R a+rwX /var/www/html' \
        >/dev/null 2>&1 || true
else
    chmod -R a+rwX "$ROOT/woltlab" 2>/dev/null || true
fi
msg "✓ Download fertig." "✓ Download complete."
