# python-coverage-comment

Create a Coverage report comment on Github PR

Permissions needed for the Github Token:

`Pull requests:read`
`Pull requests:write`

If you have given `ANNOTATIONS_DATA_BRANCH` branch then Github Token also requires content write permissions.
Read more on how to use this [here](./docs/annotations.md).

`Contents:read`
`Contents:write`

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
- `GITHUB_PR_NUMBER`: The number of the pull request where the action is running. (Optional)
- `GITHUB_REF`: The branch to run the action on. If not provided, it will be used to get the PR number. (Optional)

Note: Either `GITHUB_PR_NUMBER` or `GITHUB_REF` is required. `GITHUB_PR_NUMBER` takes precedence if both mentioned.

## Optional Environment Variables

- `SUBPROJECT_ID`: The ID or URL of the subproject or report.
- `MINIMUM_GREEN`: The minimum coverage percentage for green status. Default is 100.
- `MINIMUM_ORANGE`: The minimum coverage percentage for orange status. Default is 70.
- `BRANCH_COVERAGE`: Show branch coverage in the report. Default is False.
- `SKIP_COVERAGE`: Skip coverage reporting as github comment and generate only annotaions. Default is False.
- `ANNOTATIONS_DATA_BRANCH`: The branch to store the annotations. Read more about this [here](./docs/annotations.md).
- `ANNOTATIONS_OUTPUT_PATH`: The path where the annotaions should be stored. Should be a path to folder.
- `ANNOTATE_MISSING_LINES`: Whether to annotate missing lines in the coverage report. Default is False.
- `ANNOTATION_TYPE`: The type of annotation to use for missing lines. 'notice' or 'warning' or 'error'. Default is 'warning'.
- `MAX_FILES_IN_COMMENT`: The maximum number of files to include in the coverage report comment. Default is 25.
- `COMPLETE_PROJECT_REPORT`: Whether to include the complete project coverage report in the comment. Default is False.
- `COVERAGE_REPORT_URL`: URL of the full coverage report to mention in the comment.
- `DEBUG`: Whether to enable debug mode. Default is False.

## Setting up Local Environment using Pipenv

To get started, follow these steps:

1. Clone the repository:

    ```bash
    git clone <repository_url>
    ```

2. Navigate to the cloned repository:

    ```bash
    cd <repository_directory>
    ```

3. create `.env`:

    ```bash
    echo "PIPENV_VENV_IN_PROJECT=1" >> .env
    ```

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
> This project is almost copy of
> [py-cov-action/python-coverage-comment-action](<https://github.com/py-cov-action/python-coverage-comment-action.git>),
> [LICENSE](<https://github.com/py-cov-action/python-coverage-comment-action/blob/main/LICENSE>) with few modifications.
---
