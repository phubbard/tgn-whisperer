# Pull Request Workflow

Now that there are multiple collaborators, we use a PR-based workflow instead of pushing directly to `main`.

## Setting Up Branch Protection

### 1. Enable Branch Protection on GitHub

Go to your repository settings and protect the `main` branch:

```
Settings → Branches → Add branch protection rule
```

Configure:
- **Branch name pattern**: `main`
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: 1
- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - Add status check: `test` (from your GitHub Actions workflow)
- ✅ **Do not allow bypassing the above settings** (even for admins)

### 2. Update Local Workflow

#### For New Features/Fixes

```bash
# 1. Make sure main is up to date
git checkout main
git pull origin main

# 2. Create a feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description

# 3. Make your changes
# ... edit files ...

# 4. Commit changes
git add .
git commit -m "Description of changes"

# 5. Push branch to GitHub
git push origin feature/your-feature-name

# 6. Create PR on GitHub
# Go to https://github.com/phubbard/tgn-whisperer/pulls
# Click "New pull request"
# Select your branch → Create pull request
```

#### For Claude Code

When Claude makes changes, it will:
1. Create a feature branch (e.g., `claude/fix-logging-issue`)
2. Commit changes to that branch
3. Push the branch to GitHub
4. Create a pull request
5. Wait for human review and approval

To enable this, Claude needs to be told to use branches:
- When asking Claude to make changes, you can say: "Create a PR for this" or "Use a feature branch"
- Claude will automatically create appropriately named branches like `claude/feature-description`

### 3. Reviewing and Merging PRs

#### Review Process

1. Go to https://github.com/phubbard/tgn-whisperer/pulls
2. Click on the PR to review
3. Check the **Files changed** tab to see what was modified
4. Check the **Checks** tab to ensure tests pass
5. Leave comments if needed
6. Click **Review changes** → **Approve** (or **Request changes**)

#### Merging

Once approved and tests pass:
1. Click **Merge pull request**
2. Choose merge strategy:
   - **Squash and merge** (recommended) - combines all commits into one
   - **Rebase and merge** - replays commits on top of main
   - **Create merge commit** - traditional merge
3. Click **Confirm merge**
4. Delete the branch after merging (GitHub will prompt you)

### 4. Automated Workflow (Cron Job)

The daily cron job at 7:02 AM runs from the `main` branch:

```bash
# ~/bin/tgn-prefect
cd ~/code/tgn-whisperer
git pull origin main  # Update to latest
uv run python app/run_prefect.py
```

This ensures the production workflow always uses approved, merged code.

## Branch Naming Conventions

Use descriptive branch names with prefixes:

- `feature/` - New features (e.g., `feature/add-rss-cache`)
- `fix/` - Bug fixes (e.g., `fix/transcription-timeout`)
- `refactor/` - Code refactoring (e.g., `refactor/simplify-attribution`)
- `docs/` - Documentation updates (e.g., `docs/update-readme`)
- `claude/` - Changes made by Claude Code (e.g., `claude/improve-logging`)

## Best Practices

1. **Keep PRs focused** - One feature or fix per PR
2. **Write descriptive commit messages** - Explain what and why
3. **Update tests** - Add/update tests for new features or fixes
4. **Keep branches short-lived** - Merge within a few days
5. **Pull main regularly** - Stay up to date to avoid conflicts
6. **Delete merged branches** - Keep the repository clean

## Emergency Hotfixes

If you need to bypass the PR process for urgent fixes:

1. Ask a repository admin to temporarily disable branch protection
2. Make the fix directly on `main`
3. Push immediately
4. Re-enable branch protection
5. Document what happened in commit message

Note: This should be rare. Most "urgent" fixes can wait for a quick PR review.

## GitHub Actions

The `.github/workflows/test.yml` workflow runs automatically on:
- Every push to any branch
- Every pull request to `main`

Tests must pass before a PR can be merged.

## Questions?

- **"Can I push directly to main?"** - No, not after branch protection is enabled
- **"What if tests fail?"** - Fix the issue in your branch and push again
- **"Can I merge my own PR?"** - Technically yes, but best practice is to have someone else review
- **"What if I forget to create a branch?"** - You can create one from your current commits:
  ```bash
  git checkout -b feature/forgot-branch
  git push origin feature/forgot-branch
  ```
