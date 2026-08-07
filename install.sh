#!/usr/bin/env bash
set -euo pipefail

# Keep this URL aligned with config/defaults.env for raw-script bootstrap.
DEFAULT_REPO_ARCHIVE_URL="https://github.com/tbladh/pollyanna-skill/archive/refs/heads/main.tar.gz"
SCRIPT_SOURCE="${BASH_SOURCE:-$0}"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_SOURCE}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}"
ARCHIVE_TMP_DIR=""
RENDER_ROOT=""
INSTALL_LEGACY_CODEX=0
ASSUME_YES=0
TARGET_MODE="all"
INSTALL_HOME_DIR="${POLLYANNA_INSTALL_HOME:-${HOME}}"

usage() {
  cat <<'EOF'
Usage: install.sh [options]

Install Pollyanna globally for Codex, Claude, Cursor, Kiro, Cline, GitHub Copilot, and Windsurf.

Options:
  --all               Install to the default broad harness set
  --codex             Install only to Codex
  --claude            Install only to Claude
  --cursor            Install only to Cursor
  --kiro              Install only to Kiro
  --cline             Install only to Cline
  --copilot           Install only to GitHub Copilot
  --windsurf          Install only to Windsurf
  --legacy-codex      Also install to the legacy Codex skills path
  --no-legacy-codex   Do not install to the legacy Codex skills path (default)
  --yes               Replace existing installed folders without prompting
  --help              Show this help text

Environment:
  POLLYANNA_REPO_ARCHIVE_URL  Override the GitHub archive used by raw-script bootstrap.
  POLLYANNA_INSTALL_HOME      Override the user home used for installation targets.
EOF
}

cleanup() {
  if [[ -n "${ARCHIVE_TMP_DIR}" && -d "${ARCHIVE_TMP_DIR}" ]]; then
    rm -rf "${ARCHIVE_TMP_DIR}"
  fi
  if [[ -n "${RENDER_ROOT}" && -d "${RENDER_ROOT}" ]]; then
    rm -rf "${RENDER_ROOT}"
  fi
}

trap cleanup EXIT

load_env_file() {
  local env_file="$1"
  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  set +a
}

require_command() {
  local command_name="$1"
  local purpose="$2"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Pollyanna needs ${command_name} ${purpose}, but it was not found on PATH." >&2
    return 127
  fi
}

resolve_repo_root() {
  if [[ -f "${REPO_ROOT}/config/defaults.env" && -d "${REPO_ROOT}/template/skill" ]]; then
    printf '%s\n' "${REPO_ROOT}"
    return 0
  fi

  require_command curl "to download the repository archive"
  require_command tar "to extract the repository archive"

  local archive_url="${POLLYANNA_REPO_ARCHIVE_URL:-${DEFAULT_REPO_ARCHIVE_URL}}"
  ARCHIVE_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/pollyanna-install.XXXXXX")"
  local archive_path="${ARCHIVE_TMP_DIR}/repo.tar.gz"
  curl -fsSL "${archive_url}" -o "${archive_path}"
  tar -xzf "${archive_path}" -C "${ARCHIVE_TMP_DIR}"

  local extracted_root
  extracted_root="$(find "${ARCHIVE_TMP_DIR}" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  if [[ -z "${extracted_root}" || ! -f "${extracted_root}/config/defaults.env" ]]; then
    echo "Could not find a Pollyanna repository in ${archive_url}." >&2
    return 1
  fi

  printf '%s\n' "${extracted_root}"
}

run_python() {
  if command -v python3 >/dev/null 2>&1; then
    python3 "$@"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    python "$@"
    return
  fi
  if command -v py >/dev/null 2>&1; then
    py -3 "$@"
    return
  fi
  echo "Pollyanna installer needs Python 3, but no Python launcher was found on PATH." >&2
  return 127
}

confirm_replace() {
  local harness="$1"
  local path="$2"

  if [[ ! -e "${path}" || "${ASSUME_YES}" -eq 1 ]]; then
    return 0
  fi

  if [[ ! -t 0 ]]; then
    printf '%s\n' \
      "Skipped ${harness}: installer input is not interactive." \
      "Rerun with --yes to replace ${path}." >&2
    return 1
  fi

  local reply=""
  if ! { exec 3<>/dev/tty; } 2>/dev/null; then
    printf '%s\n' \
      "Skipped ${harness}: installer input is not interactive." \
      "Rerun with --yes to replace ${path}." >&2
    return 1
  fi

  printf 'Replace existing %s install at %s? [y/N] ' "${harness}" "${path}" >&3
  read -r reply <&3 || true
  exec 3>&-
  case "${reply}" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

install_one() {
  local harness="$1"
  local root_dir="$2"
  local skill_name="$3"
  local rendered_skill_dir="$4"
  local dest_dir="${root_dir}/${skill_name}"
  local stage_dir="${root_dir}/.${skill_name}.new.$$"
  local backup_dir="${root_dir}/.${skill_name}.previous.$$"

  mkdir -p "${root_dir}"
  if ! confirm_replace "${harness}" "${dest_dir}"; then
    echo "Skipped ${harness}."
    return 0
  fi

  rm -rf "${stage_dir}" "${backup_dir}"
  cp -R "${rendered_skill_dir}" "${stage_dir}"

  if [[ -e "${dest_dir}" ]]; then
    mv "${dest_dir}" "${backup_dir}"
  fi

  if ! mv "${stage_dir}" "${dest_dir}"; then
    [[ -e "${backup_dir}" ]] && mv "${backup_dir}" "${dest_dir}"
    echo "Could not install ${harness}; restored the previous install." >&2
    return 1
  fi

  rm -rf "${backup_dir}"
  echo "Installed ${harness}: ${dest_dir}"
}

ensure_memory_template() {
  local memory_dir="${INSTALL_HOME_DIR}/${HOME_ROOT_NAME}/${DOCS_SUBDIR}"
  local memory_file="${memory_dir}/${MEMORY_FILE_NAME}"

  mkdir -p "${memory_dir}"
  if [[ -e "${memory_file}" ]]; then
    echo "Memory exists: ${memory_file}"
    return 0
  fi

  cat >"${memory_file}" <<EOF
# ${PRODUCT_TITLE} Memory

This local file stores durable collaboration preferences learned by ${PRODUCT_TITLE}. Keep it concise and never store secrets, credentials, tokens, sensitive personal information, or private source content.

## Collaboration Preferences


## Useful Context


## Approaches That Work


## Overrides

EOF
  echo "Created memory: ${memory_file}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) TARGET_MODE="all" ;;
    --codex|--claude|--cursor|--kiro|--cline|--copilot|--windsurf)
      [[ "${TARGET_MODE}" == "all" ]] && TARGET_MODE=""
      TARGET_MODE="${TARGET_MODE} $1"
      ;;
    --legacy-codex) INSTALL_LEGACY_CODEX=1 ;;
    --no-legacy-codex) INSTALL_LEGACY_CODEX=0 ;;
    --yes) ASSUME_YES=1 ;;
    --help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
  shift
done

REPO_ROOT="$(resolve_repo_root)"
load_env_file "${REPO_ROOT}/config/defaults.env"

RENDER_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/pollyanna-render.XXXXXX")"
RENDERED_SKILL_DIR="$(run_python "${REPO_ROOT}/scripts/render_skill.py" --repo-root "${REPO_ROOT}" --output-dir "${RENDER_ROOT}")"

if [[ ! -d "${RENDERED_SKILL_DIR}" ]]; then
  echo "Rendered skill directory not found: ${RENDERED_SKILL_DIR}" >&2
  exit 1
fi

declare -a TARGETS=()
if [[ "${TARGET_MODE}" == "all" ]]; then
  TARGETS=(codex claude cursor kiro cline)
else
  for item in ${TARGET_MODE}; do
    TARGETS+=("${item#--}")
  done
fi

for target in "${TARGETS[@]}"; do
  case "${target}" in
    codex) install_one "Codex" "${INSTALL_HOME_DIR}/.agents/skills" "${PRODUCT_NAME}" "${RENDERED_SKILL_DIR}" ;;
    claude) install_one "Claude" "${INSTALL_HOME_DIR}/.claude/skills" "${PRODUCT_NAME}" "${RENDERED_SKILL_DIR}" ;;
    cursor) install_one "Cursor" "${INSTALL_HOME_DIR}/.cursor/skills" "${PRODUCT_NAME}" "${RENDERED_SKILL_DIR}" ;;
    kiro) install_one "Kiro" "${INSTALL_HOME_DIR}/.kiro/skills" "${PRODUCT_NAME}" "${RENDERED_SKILL_DIR}" ;;
    cline) install_one "Cline" "${INSTALL_HOME_DIR}/.cline/skills" "${PRODUCT_NAME}" "${RENDERED_SKILL_DIR}" ;;
    copilot) install_one "GitHub Copilot" "${INSTALL_HOME_DIR}/.copilot/skills" "${PRODUCT_NAME}" "${RENDERED_SKILL_DIR}" ;;
    windsurf) install_one "Windsurf" "${INSTALL_HOME_DIR}/.codeium/windsurf/skills" "${PRODUCT_NAME}" "${RENDERED_SKILL_DIR}" ;;
  esac
done

if [[ "${INSTALL_LEGACY_CODEX}" -eq 1 ]]; then
  LEGACY_BASE="${CODEX_HOME:-${INSTALL_HOME_DIR}/.codex}"
  install_one "Codex legacy" "${LEGACY_BASE}/skills" "${PRODUCT_NAME}" "${RENDERED_SKILL_DIR}"
fi

ensure_memory_template
