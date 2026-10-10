#!/usr/bin/env bash
set -euo pipefail

if (($# != 1)); then
  echo "Usage: $0 <project-directory>" >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "${script_dir}/.." && pwd)"
project_dir="${repo_dir}/${1}"
op_item="${1//_/-}"
s3_prefix="${op_item}"
prompt_dir="${project_dir}/infra/prompts"
knowledge_dir="${repo_dir}/knowledge"
bucket="hive"
s3_endpoint="https://s3.timcasa.me"

command -v op >/dev/null 2>&1 || {
  echo "1Password CLI (op) is required" >&2
  exit 1
}

export AWS_ACCESS_KEY_ID="$(op read "op://homelab/${op_item}/S3_ACCESS_KEY_ID")"
export AWS_SECRET_ACCESS_KEY="$(op read "op://homelab/${op_item}/S3_SECRET_ACCESS_KEY")"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_EC2_METADATA_DISABLED=true
export AWS_S3_ADDRESSING_STYLE=path

aws --endpoint-url "${s3_endpoint}" s3 cp \
  "${prompt_dir}/" \
  "s3://${bucket}/${s3_prefix}/prompts/" \
  --recursive \
  --no-progress

aws --endpoint-url "${s3_endpoint}" s3 cp \
  "${knowledge_dir}/" \
  "s3://${bucket}/${s3_prefix}/knowledge/" \
  --recursive \
  --exclude "README.md" \
  --no-progress

checksum="$(sha256sum "${prompt_dir}/system.md" | awk '{print $1}')"
echo "Uploaded prompts to s3://${bucket}/${s3_prefix}/prompts/"
echo "Uploaded knowledge to s3://${bucket}/${s3_prefix}/knowledge/"
echo "Set prompt_sha256 to: ${checksum}"
