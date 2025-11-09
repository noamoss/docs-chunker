# Pre-commit Setup

Pre-commit hooks have been installed and configured to run automatically before commits.

## What's Installed

The following hooks are configured in `.pre-commit-config.yaml`:

1. **pre-commit-hooks**: Basic checks (trailing whitespace, end-of-file, YAML/JSON/TOML validation, etc.)
2. **ruff**: Linting and formatting (runs automatically with `--fix`)
3. **ruff-format**: Code formatting
4. **black**: Code formatting (backup/consistency)
5. **detect-secrets**: Secret scanning
6. **pytest**: Runs tests (requires pytest to be installed)

## How It Works

When you run `git commit`, the pre-commit hooks will automatically:
- Run ruff linting and auto-fix issues
- Format code with ruff-format and black
- Check for secrets
- Run tests (if pytest is available)

**If any hook fails, the commit will be blocked** until issues are fixed.

## Manual Execution

You can manually run all hooks on all files:
```bash
python3 -m pre_commit run --all-files
```

Or run on staged files only:
```bash
python3 -m pre_commit run
```

## Installation Status

✅ Pre-commit hooks installed at `.git/hooks/pre-commit`
✅ Hooks will run automatically on `git commit`
✅ Hooks configured to use Python 3 from system

## Troubleshooting

If hooks don't run:
1. Verify installation: `python3 -m pre_commit --version`
2. Reinstall hooks: `python3 -m pre_commit install`
3. Check hook file exists: `ls -la .git/hooks/pre-commit`

If pytest hook fails:
- Install pytest: `pip install pytest` or use the dev dependencies
- Or modify `.pre-commit-config.yaml` to make pytest optional
