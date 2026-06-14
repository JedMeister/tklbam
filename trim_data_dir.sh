#!/bin/bash -eu

dir="/var/lib/deckdebuilds/chroots/turnkey-python-botocore-1.37.9+repack-1+1+g410a348/home/build/aws_data"

to_keep=( sts s3 )

start_size=$(du -sh "$dir")

echo "##### cleaning data dirs"
echo "#*# start size: $start_size"


for item in "$dir"/*; do
    if [[ -d "$item" ]]; then
        name=$(basename "$item")
        remove_dir="$item"
        for keep_dir in "${to_keep[@]}"; do
            if [[ "$name" == "$keep_dir" ]]; then
                remove_dir=""
            fi
        done
        if [[ -n "$remove_dir" ]]; then
            echo "# '$name' doesn't match any of '${to_keep[*]}' - deleting"
            rm -r "$remove_dir"
        else
            echo "#* '$name' matches one of '${to_keep[*]}' - skipping"
        fi
    fi
done

cat <<EOF

##### finished cleaning data dirs

Summary:

start size: $start_size
end size:   $(du -sh "$dir")
EOF
