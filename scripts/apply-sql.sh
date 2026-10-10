#!/usr/bin/env bash
set -Eeuo pipefail

if (($# != 2)); then
  echo "Usage: $0 <project-directory> <1password-password-reference>" >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "${script_dir}/.." && pwd)"
project_dir="$1"
[[ "${project_dir}" = /* ]] || project_dir="${repo_dir}/${project_dir}"
password_reference="$2"

project_version="$(awk -F'"' '/^version = "/ { print $2; exit }' "${project_dir}/pyproject.toml")"
sql_dir="${project_dir}/infra/sql/${project_version}"

command -v psql >/dev/null 2>&1 || {
  echo "psql is required; run task setup or install the PostgreSQL client" >&2
  exit 1
}
command -v op >/dev/null 2>&1 || {
  echo "1Password CLI (op) is required" >&2
  exit 1
}

export PGPASSWORD="$(op read "${password_reference}")"

: "${PGHOST:?PGHOST must be set}"
: "${PGPORT:?PGPORT must be set}"
: "${PGDATABASE:?PGDATABASE must be set}"
: "${PGUSER:?PGUSER must be set}"

mapfile -d '' sql_files < <(find "${sql_dir}" -type f -name '*.sql' -print0 | sort -z)
if ((${#sql_files[@]} == 0)); then
  echo "No SQL files found below ${sql_dir}" >&2
  exit 1
fi

for sql_file in "${sql_files[@]}"; do
  psql --no-password --set ON_ERROR_STOP=1 --file "${sql_file}"
done
