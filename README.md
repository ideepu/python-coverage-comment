# python-coverage-comment

Create a Coverage report comment on Github PR

To generate the pytest coverage report

```bash
pipenv run pytest tests  --cov-branch --cov=codecov --cov-report=json:/tmp/report.json
```

Permissions needed for the Github Token:

`Contents:read`
`Pull requests:read`
`Pull requests:write`

If you have given `ANNOTATIONS_DATA_BRANCH` branch then Github Token also requires content write permissions.
Read more on how to use this [here](./docs/annotations.md).

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

3. Build the project:

    ```bash
    make all
    ```

4. **Export the required environment variables**:

    ```bash
    export GITHUB_REPOSITORY=<repository_name>
    export COVERAGE_PATH=<path_to_coverage_report>
    export GITHUB_TOKEN=<github_token>
    export GITHUB_PR_NUMBER=<pull_request_number>
    ```

5. **Run the action**:

    ```bash
    make run
    ```

## Required Environment Variables

- `GITHUB_REPOSITORY`: The name of the GitHub repository where the action is running.
- `COVERAGE_PATH`: The path to the coverage report file. (JSON format)
- `GITHUB_TOKEN`: The GitHub token used for authentication.
- `GITHUB_PR_NUMBER`: The number of the pull request where the action is running. (Optional)
- `GITHUB_REF`: The branch to run the action on. If not provided, it will be used to get the PR number. (Optional)

Note: Either `GITHUB_PR_NUMBER` or `GITHUB_REF` is required.

## Optional Environment Variables

- `GITHUB_BASE_REF`: The base branch for the pull request. Default is `main`.
- `SUBPROJECT_ID`: The ID or URL of the subproject or report.
- `MINIMUM_GREEN`: The minimum coverage percentage for green status. Default is 100.
- `MINIMUM_ORANGE`: The minimum coverage percentage for orange status. Default is 70.
- `BRANCH_COVERAGE`: Show branch coverage in the report. Default is False.
- `SKIP_COVERAGE`: Skip coverage reporting as github comment and generate only annotaions. Default is False.
- `ANNOTATIONS_DATA_BRANCH`: The branch to store the annotations. Read more about this [here](./docs/annotations.md).
- `ANNOTATIONS_OUTPUT_PATH`: The path where the annotaions should be stored. Should be a .json file.
- `ANNOTATE_MISSING_LINES`: Whether to annotate missing lines in the coverage report. Default is False.
- `ANNOTATION_TYPE`: The type of annotation to use for missing lines. Default is 'warning'.
- `MAX_FILES_IN_COMMENT`: The maximum number of files to include in the coverage report comment. Default is 25.
- `COMPLETE_PROJECT_REPORT`: Whether to include the complete project coverage report in the comment. Default is False.
- `COVERAGE_REPORT_URL`: URL of the full coverage report to mention in the comment.
- `DEBUG`: Whether to enable debug mode. Default is False.

That's it! You have successfully cloned the repository and built the project.

## Custom Installation

1. Install Python: Make sure you have Python installed on your system.
You can download and install Python from the official Python website.

2. Install Pipenv: Pipenv is a package manager that combines pip and virtualenv.
You can install Pipenv using pip, the Python package installer.
Open your terminal or command prompt and run the following command:

    ```bash
    pip install pipenv
    ```

3. Install project dependencies:
To install the project dependencies specified in the Pipfile, run the following command:

    ```bash
    pipenv install --dev
    ```

4. Activate the virtual environment:
To activate the virtual environment created by Pipenv, run the following command:

    ```bash
    pipenv shell
    ```

5. Run your project:
You can now run your project using the activated virtual environment.
For example, if your project has a run.py file, you can run it using the following command:

    ```bash
    python run.py
    ```

6. Install pre-commit hooks: To set up pre-commit hooks for your project, run the following command:

    ```bash
    pipenv run pre-commit install
    ```

    This will install and configure pre-commit hooks that will run before each commit to enforce code quality and style standards.

That's it! You have successfully set up your local environment using Pipenv.

This project is almost copy of [py-cov-action/python-coverage-comment-action]
(<https://github.com/py-cov-action/python-coverage-comment-action.git>) with few modifications.
