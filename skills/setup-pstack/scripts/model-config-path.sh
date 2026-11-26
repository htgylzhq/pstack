#!/bin/sh

set -eu

usage() {
    printf '%s\n' 'Usage: model-config-path.sh list | read|write HARNESS_ID' >&2
    exit 2
}

case "$#:${1:-}" in
    1:list|2:read|2:write) ;;
    *) usage ;;
esac

skill_dir=$(cd "$(dirname "$0")/.." >/dev/null && pwd -P)
registry_name=model-config-routes.conf
user_registry="$HOME/.agents/pstack/$registry_name"
if [ -e "$user_registry" ] || [ -L "$user_registry" ]; then
    registry=$user_registry
else
    claude_home=${CLAUDE_CONFIG_DIR:-}
    case "$claude_home" in
        /*) ;;
        *) claude_home="$HOME/.claude" ;;
    esac
    # shortcut: only Claude Code's global dir, add others when a harness reports one
    for registry in \
        "$skill_dir/references/$registry_name" \
        "$(dirname "$skill_dir")/setup-pstack/references/$registry_name" \
        "$HOME/.agents/skills/setup-pstack/references/$registry_name" \
        "${claude_home%/}/skills/setup-pstack/references/$registry_name" \
        "$HOME/.claude/skills/setup-pstack/references/$registry_name"; do
        if [ -e "$registry" ] || [ -L "$registry" ]; then
            break
        fi
        registry=
    done
fi

if [ -z "$registry" ]; then
    printf '%s\n' 'No pstack routing table found. Install setup-pstack with this skill or supply a user routing table.' >&2
    exit 1
fi
if [ ! -f "$registry" ] || [ ! -r "$registry" ]; then
    printf 'Cannot read pstack routing table: %s\n' "$registry" >&2
    exit 1
fi

route=$(awk -F '|' -v mode="$1" -v harness="${2:-}" '
    function invalid(message) {
        printf "%s:%d: %s\n", FILENAME, FNR, message > "/dev/stderr"
        failed = 1
        exit 1
    }
    {
        sub(/\r$/, "")
    }
    /^[[:space:]]*(#|$)/ { next }
    {
        if (NF < 2 || NF > 7 || $2 == "" ||
            ($3 != "" && $3 !~ /^[A-Z_][A-Z0-9_]*$/) ||
            ($4 != "" && ($3 == "" || $4 ~ /^\//)) ||
            $5 ~ /\// || $5 == "." || $5 == ".." ||
            ($7 != "" && ($3 == "" || ($7 != "relative" && $7 != "profile"))))
            invalid("invalid model config route")
        count = split($1, ids, ",")
        if (count == 0)
            invalid("missing harness ID")
        for (i = 1; i <= count; i++) {
            id = ids[i]
            if (id !~ /^[a-z0-9][a-z0-9-]*$/)
                invalid("invalid harness ID: " id)
            if (seen[id]++)
                invalid("duplicate harness ID: " id)
            if (id == harness)
                selected = $0
            ids_in_order[++total] = id
        }
    }
    END {
        if (failed)
            exit 1
        if (total == 0)
            invalid("no model config routes")
        if (mode == "list") {
            for (i = 1; i <= total; i++)
                print ids_in_order[i]
        } else if (selected == "") {
            invalid("unknown harness ID: " harness)
        } else {
            print selected
        }
    }
' "$registry")

if [ "$1" = list ]; then
    printf '%s\n' "$route"
    exit 0
fi

IFS='|' read -r ids config_dir env_name env_dir filename fallback env_policy <<EOF
$route
EOF
case "$config_dir" in
    /*) ;;
    *) config_dir="$HOME/$config_dir" ;;
esac

if [ -n "$env_name" ]; then
    env_root=$(printenv "$env_name" || :)
    case "$env_policy" in
        relative) ;;
        *)
            case "$env_root" in
                /*) ;;
                *) env_root= ;;
            esac
            ;;
    esac
    if [ "$env_policy" = profile ] && [ -n "$env_root" ]; then
        case "$HOME/" in
            "${env_root%/}/"*) env_root= ;;
        esac
    fi
    if [ -n "$env_root" ]; then
        case "$env_root" in /*) ;; *) env_root="$PWD/$env_root" ;; esac
        config_dir="${env_root%/}${env_dir:+/$env_dir}"
    fi
fi

config_path="${config_dir%/}/${filename:-pstack-models.md}"
if [ "$1" = read ] && [ -n "$fallback" ] && [ ! -e "$config_path" ] && [ ! -L "$config_path" ]; then
    case "$fallback" in
        /*) config_path=$fallback ;;
        *) config_path="$HOME/$fallback" ;;
    esac
fi

printf '%s\n' "$config_path"
