import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


repo = Path(__file__).resolve().parents[1]
registry_name = 'model-config-routes.conf'
registry_relative = Path('references') / registry_name
table = repo / 'skills/setup-pstack' / registry_relative
subprocess.run(['sh', repo / 'mirror-assets/sync-model-settings.sh', '--check'], check=True)
assert list((repo / 'skills').rglob(registry_name)) == [table]

rows = [line.split('|') for line in table.read_text().splitlines() if line and not line.startswith('#')]
canonical_ids = [row[0].split(',')[0] for row in rows]
route_ids = [harness for row in rows for harness in row[0].split(',')]
if len(sys.argv) == 2:
    upstream_source = Path(sys.argv[1]).read_text().split('export interface Skill', 1)[0]
    upstream_ids = set(re.findall(r"\| '([^']+)'", upstream_source))
    assert upstream_ids, 'Expected npx skills src/types.ts'
    assert set(canonical_ids) == upstream_ids, set(canonical_ids) ^ upstream_ids

with TemporaryDirectory(prefix='pstack-test-') as directory:
    root = Path(directory)
    profile_home = root / 'home with spaces'
    shared = profile_home / '.agents/pstack-models.md'
    shared.parent.mkdir(parents=True)
    shared.write_text('bug-fix: model-for-another-harness\n')
    user_table = profile_home / '.agents/pstack' / registry_name
    user_table.parent.mkdir()

    # A selectively installed reader can use a global setup skill or a user table.
    installed = root / 'workspace/.agents/skills/arena'
    shutil.copytree(repo / 'skills/arena', installed)
    resolver = installed / 'scripts/model-config-path.sh'
    global_setup = profile_home / '.agents/skills/setup-pstack'
    environment = {'HOME': str(profile_home), 'PATH': os.defpath}

    def invoke(*args, script=resolver, **overrides):
        return subprocess.run(
            ['sh', script, *args],
            cwd=root,
            env={**environment, **overrides},
            capture_output=True,
            text=True,
        )

    def resolve(mode, harness, **options):
        result = invoke(mode, harness, **options)
        assert result.returncode == 0, result.stderr
        return Path(result.stdout.removesuffix('\n'))

    def reject(*args, error, status=None):
        result = invoke(*args)
        assert result.returncode != 0 and not result.stdout and error in result.stderr, result
        if status is not None:
            assert result.returncode == status, result

    reject('read', 'codex', error='No pstack routing table found')
    claude_setup = profile_home / '.claude/skills/setup-pstack'
    shutil.copytree(repo / 'skills/setup-pstack', claude_setup)
    assert resolve('read', 'codex') == profile_home / '.codex/pstack-models.md'
    shutil.rmtree(claude_setup)
    custom_claude = root / 'claude-profile'
    shutil.copytree(repo / 'skills/setup-pstack', custom_claude / 'skills/setup-pstack')
    assert resolve('read', 'codex', CLAUDE_CONFIG_DIR=str(custom_claude)) == profile_home / '.codex/pstack-models.md'
    reject('read', 'codex', error='No pstack routing table found')
    shutil.copytree(repo / 'skills/setup-pstack', claude_setup)
    custom_claude.joinpath('skills/setup-pstack/references', registry_name).unlink()
    assert resolve('read', 'codex', CLAUDE_CONFIG_DIR=str(custom_claude)) == profile_home / '.codex/pstack-models.md'
    shutil.rmtree(claude_setup)
    shutil.rmtree(custom_claude)
    user_table.write_text('codex|custom\n')
    assert resolve('read', 'codex') == profile_home / 'custom/pstack-models.md'
    user_table.unlink()

    shutil.copytree(repo / 'skills/setup-pstack', global_setup)
    setup_resolver = global_setup / 'scripts/model-config-path.sh'
    listed = invoke('list')
    assert listed.returncode == 0 and listed.stdout.splitlines() == route_ids, listed

    default_paths = {harness: resolve('write', harness) for harness in canonical_ids}
    assert len(set(default_paths.values())) == len(canonical_ids)
    assert all(path.is_absolute() for path in default_paths.values())
    assert resolve('read', 'cursor') == profile_home / '.cursor/rules/pstack-models.mdc'
    assert resolve('read', 'universal') == resolve('read', 'other') == shared
    for harness, relative in {
        'codex': '.codex',
        'devin': '.config/devin',
        'kiro': '.kiro',
        'gemini-cli': '.gemini',
        'github-copilot': '.copilot',
        'opencode': '.config/opencode',
        'pi': '.pi/agent',
        'droid': '.factory',
        'zed': '.config/zed',
        'cline': '.config/pstack/harnesses/cline',
    }.items():
        assert resolve('read', harness) == resolve('write', harness) == profile_home / relative / 'pstack-models.md'
    assert resolve('read', 'kiro-crew') == resolve('read', 'kiro-cli')
    assert resolve('read', 'devin-local') == resolve('read', 'devin')

    claude = profile_home / '.claude/rules/pstack-models.md'
    assert resolve('read', 'claude-code') == shared
    assert resolve('write', 'claude-code') == claude
    claude.parent.mkdir(parents=True)
    claude.write_text('bug-fix: model-for-claude\n')
    assert resolve('read', 'claude-code') == claude

    custom = root / 'profiles'
    for harness, variable, suffix in [
        ('codex', 'CODEX_HOME', ''),
        ('claude-code', 'CLAUDE_CONFIG_DIR', 'rules'),
        ('devin', 'XDG_CONFIG_HOME', 'devin'),
        ('opencode', 'XDG_CONFIG_HOME', 'opencode'),
        ('goose', 'XDG_CONFIG_HOME', 'goose'),
        ('pi', 'PI_CODING_AGENT_DIR', ''),
        ('kiro', 'KIRO_HOME', ''),
    ]:
        assert resolve('write', harness, **{variable: str(custom)}) == custom / suffix / 'pstack-models.md'
    assert resolve('write', 'devin', XDG_CONFIG_HOME='relative') == default_paths['devin']
    for invalid in ['relative', '/', str(root), str(profile_home)]:
        assert resolve('read', 'kiro', KIRO_HOME=invalid) == default_paths['kiro-cli']

    # A relative CODEX_HOME resolves against the caller's directory, so setup and readers agree.
    session = root / 'session'
    session.mkdir()

    def from_session(mode, script):
        result = subprocess.run(
            ['sh', script, mode, 'codex'],
            cwd=session,
            env={**environment, 'CODEX_HOME': '.codex-work'},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        return Path(result.stdout.removesuffix('\n'))

    expected = session / '.codex-work/pstack-models.md'
    assert from_session('write', setup_resolver) == from_session('read', resolver) == expected

    # Local and global installs share the user table. With no user file, prefer the local table.
    local_setup = installed.with_name('setup-pstack')
    (local_setup / registry_relative).parent.mkdir(parents=True)
    (local_setup / registry_relative).write_text('codex|local\n')
    assert resolve('read', 'codex') == profile_home / 'local/pstack-models.md'
    assert resolve('write', 'codex', script=setup_resolver) == default_paths['codex']
    user_table.write_text(f'codex|{custom}|||role-settings.md\nnew-harness|.new\n')
    for script in [resolver, setup_resolver]:
        assert resolve('read', 'codex', script=script) == custom / 'role-settings.md'
        assert resolve('write', 'codex', script=script) == custom / 'role-settings.md'
    assert resolve('read', 'new-harness') == profile_home / '.new/pstack-models.md'
    reject('read', 'opencode', error=f'{user_table}:')
    reject('read', 'opencode', error='unknown harness ID: opencode')

    user_table.write_text('codex|literal $(touch injected)\n')
    assert resolve('read', 'codex') == profile_home / 'literal $(touch injected)/pstack-models.md'
    assert not (root / 'injected').exists()
    user_table.write_text('codex|first\ncodex|second\n')
    reject('read', 'codex', error='duplicate harness ID: codex')
    user_table.write_text('codex\n')
    reject('read', 'codex', error='invalid model config route')
    user_table.unlink()
    user_table.symlink_to(root / 'missing.conf')
    reject('read', 'codex', error=f'Cannot read pstack routing table: {user_table}')
    user_table.unlink()
    assert resolve('read', 'codex') == profile_home / 'local/pstack-models.md'

    for arguments in [(), ('read',), ('typo', 'codex')]:
        reject(*arguments, error='Usage:', status=2)
    assert shared.read_text() == 'bug-fix: model-for-another-harness\n'

print(f'{len(canonical_ids)} routes, user precedence, built-in fallback, and selective installation passed.')
