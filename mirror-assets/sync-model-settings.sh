#!/bin/sh

set -eu
cd "$(dirname "$0")/../skills"

case "${1:-}" in
    '') action=copy ;;
    --check) action=check ;;
    *) printf '%s\n' 'Usage: sync-model-settings.sh [--check]' >&2; exit 2 ;;
esac

for skill in arena interrogate poteto-help poteto-mode swarm; do
    for file in scripts/model-config-path.sh references/model-settings.md; do
        source="setup-pstack/$file"
        destination="$skill/$file"
        if [ "$action" = check ]; then
            cmp "$source" "$destination"
        else
            mkdir -p "$(dirname "$destination")"
            cp "$source" "$destination"
        fi
    done
done
