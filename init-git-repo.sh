#!/usr/bin/env bash

# TODO rewrite in python

# TODO add new versions to existing repo

extension_id="$1"
if [ -z "$extension_id" ]; then
  echo "error: missing argument: extension_id" >&2
  exit 1
fi

# validate extension id
if ! echo "$extension_id" | grep -q -E "^[a-p]{32}$"; then
  echo "error: invalid extension id: ${extension_id@Q}" >&2
  echo "the extension id must match the pattern [a-p]{32}" >&2
  exit 1
fi

if ! [ -d "$extension_id" ]; then
  echo "error: missing input files: $extension_id/*.{json,crx}" >&2
  exit 1
fi

# the *.json and *.crx files
# are produced by crx4chrome-scraper.py
json_files_path="$extension_id"
crx_files_path="$extension_id"

json_path="$json_files_path/"$(
  find "$json_files_path" -mindepth 1 -maxdepth 1 -type f -name '*.json' -printf "%P\n" |
  sort --version-sort --reverse |
  head -n1
)
echo "json_path: ${json_path@Q}"

extension_name="$(jq -r .name <"$json_path")"
echo "extension_name: ${extension_name@Q}"

extension_slug=$(echo "$extension_name" | tr "[:upper:] " "[:lower:]-")
echo "extension_slug: ${extension_slug@Q}"

repo_path="$extension_id/$extension_slug"
git_name="$extension_slug"
git_email=""

if [ -e "$repo_path" ]; then
  echo "error: output dir exists: ${repo_path@Q}" >&2
  echo "hint:" >&2
  echo "  mv -v ${repo_path@Q} ${repo_path@Q}.bak.\$(date -Is)" >&2
  exit 1
fi

mkdir "$repo_path"
git -C "$repo_path" init

while read json_name; do

  json_path="$json_files_path/$json_name"

  date=$(jq -r .date <"$json_path")
  version=$(jq -r .version <"$json_path")

  echo "date=${date@Q} version=${version@Q}"

  git -C "$repo_path" rm -r . >/dev/null 2>&1

  crx_path=$(readlink -f "$crx_files_path/$version.crx")

  # "7z x" is needed, because "unzip" restores the original file permissions
  # but the original file permissions can be broken
  # for example, folders can have "chmod 0644"
  # so accessing the folder gives "Permission denied" error

  pushd "$repo_path" >/dev/null
  7z x "$crx_path" >/dev/null
  popd >/dev/null

  git -C "$repo_path" add . >/dev/null
  d="$date""T00:00:00Z+0000"
  export GIT_AUTHOR_NAME="$git_name" GIT_COMMITTER_NAME="$git_name"
  export GIT_AUTHOR_EMAIL="$git_email" GIT_COMMITTER_EMAIL="$git_email"
  export GIT_AUTHOR_DATE="$d" GIT_COMMITTER_DATE="$d"
  git -C "$repo_path" commit -q -m "version $version"
  git -C "$repo_path" tag "$version"

done < <(
  find "$json_files_path" -mindepth 1 -maxdepth 1 -type f -name '*.json' -printf "%P\n" |
  sort --version-sort
)

echo "done $repo_path"
