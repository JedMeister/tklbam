#!/bin/bash -eu

packages=(
    python-pycurl
    pycurl-wrapper
    python-dateutil
    python-six
)

tmp_dir="$(mktemp -d)"

COMMIT_ID_PATH="$(pwd)/dep-commit-ids"

rm -f "$COMMIT_ID_PATH"

cd "$tmp_dir"
for package in "${packages[@]}"; do
    echo "# getting HEAD commit id for $package"
    HEAD=HEAD
    if [[ $package == "pycurl-wrapper" ]]; then
        HEAD=refs/heads/python2
    fi
    commit_id="$( \
        git ls-remote "https://github.com/turnkeylinux/$package" \
        | grep "$HEAD" \
        | awk '{ print $1 }' \
    )"
    echo "$package:$commit_id" | tee -a "$COMMIT_ID_PATH"
    echo
done

rm -r "$tmp_dir"
