#!/bin/bash -eu

BASE_DIR="$PWD"

PYPY_DIR=/usr/lib/tklbam-pypy2
PYPY_BIN="$PYPY_DIR/bin"
PYPY_CMD="$PYPY_BIN/pypy"

DEPROOT_LIB="$BASE_DIR/deps/lib"
DEPROOT_BIN="$BASE_DIR/deps/bin"

TMP="$BASE_DIR/debian/tmp/tklbam-deps"

export LD_LIBRARY_PATH="$PYPY_BIN"

APP=$(basename "$0")
info() { echo "[$APP] INFO: $*"; }
fatal() { echo "[$APP] ERROR: $*" >&2; exit 1; }
ch_dir() { cd "$1" || fatal "cd $1 failed"; }

mkdir -p "$TMP" "$DEPROOT_LIB" "$DEPROOT_BIN"

info "Downloading and building TurnKey deps"
while IFS= read -r line; do
    ch_dir "$TMP"
    pkg="${line%:*}"
    commit_id="${line##*:}"
    echo " - $pkg"
    org=turnkeylinux
    case "$pkg" in
        pycurl-wrapper)
            branch=python2
            ;;
        python-pycurl)
            branch=tkl
            ;;
        tklbam-duplicity)
            branch=trixie-tweaks
            org=JedMeister
            ;;
        *)
            branch=master
            ;;
    esac
    git clone --branch $branch "https://github.com/turnkeylinux/$pkg"
    ch_dir "$pkg"
    if [[ "$commit_id" != "$(git rev-parse HEAD)" ]]; then
        echo "WARNING: saved commit id for $pkg is NOT HEAD of $branch" >&2
        echo "         please update 'dep-commit-ids' to use latest" >&2
        git checkout "$commit_id"
    fi
    case "$pkg" in
        python-dateutil)
            mv "$pkg/dateutil" "$DEPROOT_LIB/"
            ;;
        *)
            "$PYPY_CMD" setup.py build
            mv "$pkg/build/lib"*/* "$DEPROOT_LIB"
            ;;&
        tklbam-duplicity)
            mv "$pkg/scripts-2.7/duplicity" "$DEPROOT_BIN/"
            ;;
    esac
done < "$BASE_DIR/dep-commit-ids"

info "Downloading and verifying pycryptodome source tarball"

ch_dir "$TMP"
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
mv "$build_dir/build/lib"*/* "$DEPROOT_LIB/"
info "TKLBAM dependencies built successfully"
