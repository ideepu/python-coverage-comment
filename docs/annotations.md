# How Annotations Work

Annotations in this context are similar to GitHub annotations or workflow commands,
displaying a banner in the GitHub pull request.
When the option `ANNOTATE_MISSING_LINES=True` is enabled, annotations are generated for lines missing coverage.
To include branch coverage in these annotations, enable `BRANCH_COVERAGE=True`.
By default, these annotations are written to the console, but you can also choose to save them elsewhere.

## Storing Annotations

1. **To a File**:
   - Set the file path in `ANNOTATIONS_OUTPUT_PATH`.

2. **To a Branch**:
   - Set the branch name in `ANNOTATIONS_DATA_BRANCH`.
   - Ensure your GitHub token has `Contents:write` permissions.
   - Make sure the branch exists and is not protected by branch protection rules.
   - Annotations are stored with the filename `{PR-number}-annotations.json`,
   where `{PR-number}` is replaced by the actual PR number.
   - Existing annotations for a PR in the branch will be overwritten if the file already exist in branch.
   - If the GitHub token user has email privacy enabled, the email format `{id}+{login}@users.noreply.github.com` is used.
   Where `{id}` is the user ID and `{login}` is the username.

## Using the Annotations

After generating the annotations, you can enable this extension.
A URL is required where the annotations are accessible from the extension, with a placeholder for the PR number.
For example:
`https://raw.githubusercontent.com/PradeepTammali/python-coverage-comment/data/coverage-annotations/{PR-NUMBER}-annotations.json`

The `{PR-NUMBER}` placeholder will be replaced with the actual PR number when viewing the PR diff.
