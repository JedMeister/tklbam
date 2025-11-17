#!/bin/bash -eu

BASE_DIR="$PWD"
DEPROOT="$BASE_DIR/lib/deps"
TMP="$BASE_DIR/debian/tmp/tklbam-deps"
HOST_ARCH=$(dpkg --print-architecture)
PYPY_DIR=/usr/lib/tklbam-pypy2

export LD_LIBRARY_PATH="$PYPY_DIR/bin"

APP=$(basename "$0")
info() { echo "[$APP] INFO: $*"; }
fatal() { echo "[$APP] ERROR: $*" >&2; exit 1; }
ch_dir() { cd "$1" || fatal "cd $1 failed"; }

mkdir -p "$DEPROOT" "$TMP"

ch_dir "$TMP"

info "cloning TurnKey repos"
while IFS= read -r line; do
    pkg="${line%:*}"
    commit_id="${line##*:}"
    git clone "https://github.com/turnkeylinux/$pkg"
    ch_dir "$pkg"
    git checkout "$commit_id"
    "$LD_LIBRARY_PATH/pypy" setup.py build
    ch_dir "$TMP"
    mv "$pkg/build/lib"*/* "$DEPROOT/site-packages"
done < "$BASE_DIR/dep-commit-ids"

info "Downloading and verifying pycryptodome source tarball"
url=https://github.com/Legrandin/pycryptodome
latest_pycrypto_url=$( \
    curl --location --silent --output /dev/null \
        --write-out "%{url_effective}\n" "$url/releases/latest" \
)
latest_pycrypto="${latest_pycrypto_url##*/}"

read -r pycrypto_checksum pycrypto_archive <<< "$( \
    sed -En "\|^[a-z0-9]+|p" "$BASE_DIR/pycryptodome.checksum.txt" \
)"
verified_pycrypto="${pycrypto_archive//.tar.gz}"

if [[ "$latest_pycrypto" != "$verified_pycrypto" ]]; then
    cat <<EOF >&2
WARNING: a new pycryptodome version is available
         - verified version: $verified_pycrypto
         - latest version: $latest_pycrypto
Please run ./update_pycryptodome.sh to update to the latest version
See also: https://github.com/Legrandin/pycryptodome/releases
EOF
fi

url=https://github.com/Legrandin/pycryptodome/archive/refs/tags
info "downloading cryptodome source: $verified_pycrypto"
curl --remote-name --location "$url/$pycrypto_archive"
if [[ $(sha256sum "$pycrypto_archive") \
    != "$pycrypto_checksum"*"$pycrypto_archive" ]]; then
        fatal "$pycrypto_archive checksum mismatch"
fi

build_dir="pycryptodome-${verified_pycrypto#v}"
info "Unpacking $pycrypto_archive and building pycryptodome $verified_pycrypto"
tar xf "$pycrypto_archive"
ch_dir "$build_dir"
"$LD_LIBRARY_PATH/pypy" setup.py build
ch_dir "$TMP"
mv "$build_dir/build/lib"*/* "$DEPROOT/site-packages"
info "TKLBAM dependencies built successfully"
