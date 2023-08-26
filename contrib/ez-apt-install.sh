#!/bin/bash -e
# script adds the correct apt source and installs package
# Author: Liraz Siri <liraz@turnkeylinux.org>

fatal() { echo "FATAL: $@" >&2; exit 1; }
info() { echo "INFO: $@"; }

[[ -z "$DEBUG" ]] || set -x

get_debian_dist() {
    case "$1" in
        9.*)  echo stretch ;;
        10.*) echo buster ;;
        11.*) echo bullseye ;;
        12.*) echo bookworm ;;
        13.*) echo trixie ;;
        */*)  echo $1 | sed 's|/.*||' ;;
    esac
}

get_tkl_ver() {
    case "$1" in
        stretch)    echo "15.x" ;;
        buster)     echo "16.x" ;;
        bullseye)   echo "17.x" ;;
        bookworm)   echo "18.x" ;;
        trixie)     echo "19.x" ;;
        *)          fatal "Debian codename '$1' not currently supported -"\
                            " please report to TurnKey";;
    esac
}

[[ -f /etc/debian_version ]] || fatal "not a Debian derived system - no /etc/debian_version file"
deb_dist=$(get_debian_dist "$(cat /etc/debian_version)")

APT_URL=${APT_URL:="http://archive.turnkeylinux.org/debian"}
base_url="https://raw.githubusercontent.com/turnkeylinux/common"
branch=$(get_tkl_ver $deb_dist)
branch_fallback="${branch}-dev"
base_path="overlays/bootstrap_apt"

KEY_FILE="usr/share/keyrings/tkl-${deb_dist}-main.gpg"
key_url="$base_url/$branch/$base_path/${KEY_FILE%gpg}asc"
key_fallback_url="$base_url/$branch_fallback/$base_path/${KEY_FILE%gpg}asc"

APT_URL=${APT_URL:="http://archive.turnkeylinux.org/debian"}
APT_KEY_URL=${APT_KEY_URL:="$key_url"}
APT_KEY_FB_URL="$key_fallback_url"

usage() {
    cat<<EOF
Syntax: $0 <package>
Script adds an apt source if needed and installs a package
Environment variables:

    PACKAGE      package to install (default: tklbam)
    APT_URL      apt source url (default: $APT_URL)
    APT_KEY_URL  apt source key url (default: $APT_KEY_URL)
EOF
    exit 1
}

[[ -n "$PACKAGE" ]] || PACKAGE="tklbam"

if [[ "$APT_KEY_URL" == *.asc ]]; then
    if ! which gpg >/dev/null 2>&1; then
        info "Installing gpg to process apt sigining key."
        apt-get update
        apt-get install -y --no-install-recommends gpg
    fi
    tmp_file=/tmp/$(basename $APT_KEY_URL)
elif [[ "$APT_KEY_URL" == *.gpg ]]; then
    tmp_file=''
else
    error "APT_KEY_URL does not appear to be a GPG file (should end with .gpg or .asc)"
fi

if ! rgrep . /etc/apt/sources.list* | sed 's/#.*//' | grep -q $APT_URL; then

    info "downloading $APT_KEY_URL"
    local_file=/$KEY_FILE
    if [[ -n "$tmp_file" ]]; then
        local_file=$tmp_file
    fi
    wget -O $local_file $APT_KEY_URL
    if file $local_file | grep -q ': empty$'; then
        info "Initial download failed, retrying dev branch"
        wget -O $local_file $APT_KEY_FB_URL
    fi
    if file $local_file | grep -q ': empty$'; then
        fatal "Key download failed, please report this to TurnKey."
    else
        info "Key downloaded, moving to /usr/share/keyrings"
        gpg -o /$KEY_FILE --dearmor $tmp_file
        rm -f $tmp_file
    fi
    apt_name=$(echo $APT_URL | sed 's|.*//||; s|/.*||')
    apt_file="/etc/apt/sources.list.d/${apt_name}.list"
    echo "deb [signed-by=/$KEY_FILE] $APT_URL $deb_dist main" > $apt_file
    info "Added $APT_URL package source to $apt_file"

fi

info "Running 'apt-get update'"
apt-get update \
    || fatal "Command failed. Please report to TurnKey Linux."

info "Installing $PACKAGE"
apt-get install $PACKAGE \
    || fatal "Package install failed, please report to TurnKey Linux."
