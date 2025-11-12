#!/bin/bash -eu

URL="https://github.com/Legrandin/pycryptodome"

latest_release_url=$( \
    curl -Ls -o /dev/null -w "%{url_effective}\n" "$URL/releases/latest" \
)
latest_version="${latest_release_url##*/}"

verified_version=$( \
    sed -En "\|^[a-z0-9]|s|^[a-z0-9]+ *(v[0-9\.]+).tar.gz|\1|p" \
        pycryptodome.checksum.txt
)

if [[ "$latest_version" == "$verified_version" ]]; then
    echo "# Already on the latest pycryptodome version: $verified_version"
    echo "# Nothing to do..."
    exit 0
fi

cat <<EOF
# A new pycryptodome release is available:
# - current version: $verified_version
# - lastest version: $latest_version
# Updating...
EOF

TMP=$(mktemp --directory pycryptodome.XXXXXX)

signing_key="pycryptodome.asc"
echo "# Importing $signing_key to local gpg keyring"
gpg --import "$signing_key"

sig="pycryptodome-${latest_version#v}.tar.gz.asc"
sig_url="$URL/releases/download/$latest_version/$sig"
tarball="$latest_version.tar.gz"
tarball_url="$URL/archive/refs/tags/$tarball"

for dl_url in "$sig_url" "$tarball_url"; do
    echo "# Downloading $dl_url to $TMP"
    wget --directory-prefix="$TMP" "$dl_url"
done

echo "# Verifying $TMP/$tarball"
if ! gpg --verify "$TMP/$sig" "$TMP/$tarball"; then
    fatal <<EOF
# Verification of $TMP/$tarball failed (sig: $TMP/$sig)
# Double check pycryptodome.asc against upstream signing key:
# https://pycryptodome.readthedocs.io/en/latest/src/installation.html#pgp-verification
EOF
    rm -rf "$TMP"
    exit 1
fi

echo "# Generating updated checksum"
TKLBAM_DIR="$PWD"
cd "$TMP"
echo "# pycryptodome checksum & filename - run ./update_pycryptodome.sh to update" \
    > "$TKLBAM_DIR/pycryptodome.checksum.txt"
sha256sum "$tarball" >> "$TKLBAM_DIR/pycryptodome.checksum.txt"
cd "$TKLBAM_DIR"
rm -rf "$TMP"
echo "# Done - confirm updated files and commit changes"
