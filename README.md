# python-coverage-comment

## WIP 🚧

Create a Coverage report comment on Github PR

Permissions needed for the Github Token:

`Pull requests:read`
`Pull requests:write`

**install:**

```bash
pip install python-coverage-comment
```

**run:**

```bash
GITHUB_REPOSITORY=<repository_name> \
COVERAGE_PATH=<path_to_coverage_report> \
GITHUB_TOKEN=<github_token> \
GITHUB_PR_NUMBER=<pull_request_number> \
codecov
```

## Required Environment Variables

- `GITHUB_REPOSITORY`: The name of the GitHub repository where the action is running.
- `COVERAGE_PATH`: The path to the coverage report file. (JSON format)
- `GITHUB_TOKEN`: The GitHub token used for authentication.
- `GITHUB_PR_NUMBER`: The number of the pull request where the coverage report comment to be generated. (Optional)
- `GITHUB_REF`: The branch name if pr number is not provided, it will be used to get the PR number. (Optional)

Note: Either `GITHUB_PR_NUMBER` or `GITHUB_REF` is required. `GITHUB_PR_NUMBER` takes precedence if both mentioned.

## Optional Environment Variables

- `MINIMUM_GREEN`: The minimum coverage percentage for green status. Default is 100.
- `MINIMUM_ORANGE`: The minimum coverage percentage for orange status. Default is 70.
- `BRANCH_COVERAGE`: Show branch coverage in the report. Default is False.
- `MAX_FILES_IN_COMMENT`: The maximum number of files to include in the coverage report comment. Default is 25.
- `SKIP_COVERED_FILES_IN_REPORT`: Skip the files with coverage 100% from the report. Default is True.
- `COMPLETE_PROJECT_REPORT`: Whether to include the complete project coverage report in the comment. Default is False.
- `LABEL`: Optional text rendered in the comment footer. Default is unset (no footer).
- `DEBUG`: Whether to enable debug mode. Default is False.

## Notes

1. The coverage report displays only files that have missing coverage. If all files are fully covered, the
   report will be empty.
2. When branch coverage is enabled, the pull request coverage percentage counts branch arcs whose source
   line is among the added lines in the diff (alongside the added statements). The `Missing branches`
   column lists those arcs as `source -> destination`. An arc that leaves its enclosing scope is shown as
   `source -> exit`.
3. In the pull request table, the `Branches` / `Missing` badges are whole-file totals from the coverage
   report, while the `Missing branches` links list only arcs on added lines. A Missing count can therefore
   be larger than the number of links shown for that file. The same pattern already applies to `Statements` /
   `Missing stmts`.
4. Pull request coverage is recalculated from the statement and branch arc lists. The report's overall
   coverage percentage comes from coverage.py's summary counts, which can still credit
   `# pragma: no branch` arcs. So, the two percentages can differ slightly even when the PR adds an entire
   file. Enable `BRANCH_COVERAGE` when your report includes branch data so both sides include branches.
5. If the complete project report option is enabled, file totals and the project coverage percentage are
   taken from the report as-is. Differences versus pull request coverage are expected when the scopes or
   formulas differ as above.

## Dev Setup

To get started, follow these steps:

1. Clone the repository:

    ```bash
    git clone <repository_url>
    ```

2. Navigate to the cloned repository:

    ```bash
    cd <repository_directory>
    ```

3. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you do not have it yet.

4. Build the project:

    ```bash
    make all
    ```

5. **Export the required environment variables**:

    ```bash
    export GITHUB_REPOSITORY=<repository_name>
    export COVERAGE_PATH=<path_to_coverage_report>
    export GITHUB_TOKEN=<github_token>
    export GITHUB_PR_NUMBER=<pull_request_number>
    ```

6. **Run the action**:

    ```bash
    make run
    ```

---
> **NOTE:**
> This project is inspired from
> [py-cov-action/python-coverage-comment-action](<https://github.com/py-cov-action/python-coverage-comment-action.git>),
> [LICENSE](<https://github.com/py-cov-action/python-coverage-comment-action/blob/main/LICENSE>) with few modifications.
---
