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
    curl -fL --progress-bar -o "$TMP_ZIP" "$ZIP_URL"
else
    URL="https://assets.woltlab.com/release/woltlab-suite-${WSC_VERSION}.zip"
    msg "↓ Lade WoltLab Suite Core ${WSC_VERSION}…" "↓ Downloading WoltLab Suite Core ${WSC_VERSION}…"
    curl -fL --progress-bar -o "$TMP_ZIP" "$URL"
    if [[ -n "${WSC_SHA256:-}" ]]; then
        echo "${WSC_SHA256}  ${TMP_ZIP}" | sha256sum -c - \
            || die "SHA-256 stimmt nicht (Datei beschädigt oder falsche Version)."
        msg "✓ SHA-256 OK" "✓ SHA-256 OK"
    fi
fi

msg "⇢ Entpacken nach ./woltlab/ …" "⇢ Extracting to ./woltlab/ …"
# ZIP kann upload/ oder Root-Dateien enthalten
TMP_DIR="$ROOT/var/extract-$$"
mkdir -p "$TMP_DIR"
unzip -q "$TMP_ZIP" -d "$TMP_DIR"

if [[ -d "$TMP_DIR/upload" ]]; then
    cp -a "$TMP_DIR/upload/." "$ROOT/woltlab/"
elif [[ -f "$TMP_DIR/install.php" ]]; then
    cp -a "$TMP_DIR/." "$ROOT/woltlab/"
else
    # ein Unterordner?
    sub=$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n1)
    if [[ -n "$sub" && -f "$sub/install.php" ]]; then
        cp -a "$sub/." "$ROOT/woltlab/"
    else
        rm -rf "$TMP_DIR"
        die "Unerwartete ZIP-Struktur (kein install.php)."
    fi
fi
rm -rf "$TMP_DIR"

[[ -f "$ROOT/woltlab/install.php" ]] || die "Nach Entpacken fehlt install.php."
msg "✓ Download fertig." "✓ Download complete."
