#!/bin/bash -eu

# dirty dev script to move installed tklbam files and create as symlinks to
# git repo source in this dir.
# this makes "real world" testing and dev "on the fly" easier and reduces
# friction and chances that commiting updates may be forgotten

DEBUG=${DEBUG:-}

[[ -z "$DEBUG" ]] || set -x

move_and_link() {
    local src=$1
    local dst_dir=$2
    local py_file
    py_file=$(basename "$src")
    mv "$dst_dir/$py_file" "$dst_dir/$py_file.bak"
    ln -s "$src" "$dst_dir/$py_file"
}

source_files="$PWD"
installed="/usr/lib/tklbam"

# not really required, but let's clean up pyc files
find "$installed" -type f -name "*.pyc" -exec rm {} +

for file in "$source_files/lib"/*.py; do
    move_and_link "$file" "$installed"
done

installed_internals="$installed/cmd_internals"
for file in "$source_files/lib/cmd_internals"/*.py; do
    move_and_link "$file" "$installed_internals"
done

installed_pylib="$installed/pylib"
for file in "$source_files/lib/pylib"/*.py; do
    move_and_link "$file" "$installed_pylib"
done
