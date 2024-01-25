# python-coverage-comment
Create a Coverage report comment on Github PR



## Setting up Local Environment using Pipenv

To get started, follow these steps:

1. Clone the repository: 
    ```
    git clone <repository_url>
    ```

2. Navigate to the cloned repository:
    ```
    cd <repository_directory>
    ```

3. Build the project:
    ```
    make all
    ```

That's it! You have successfully cloned the repository and built the project.

## Custom Installation:

1. Install Python: Make sure you have Python installed on your system. You can download and install Python from the official Python website.

2. Install Pipenv: Pipenv is a package manager that combines pip and virtualenv. You can install Pipenv using pip, the Python package installer. Open your terminal or command prompt and run the following command:
    ```
    pip install pipenv
    ```

4. Install project dependencies: To install the project dependencies specified in the Pipfile, run the following command:
    ```
    pipenv install --dev
    ```

5. Activate the virtual environment: To activate the virtual environment created by Pipenv, run the following command:
    ```
    pipenv shell
    ```

6. Run your project: You can now run your project using the activated virtual environment. For example, if your project has a run.py file, you can run it using the following command:
    ```
    python run.py
    ```

7. Install pre-commit hooks: To set up pre-commit hooks for your project, run the following command:
    ```
    pipenv run pre-commit install
    ```
    This will install and configure pre-commit hooks that will run before each commit to enforce code quality and style standards.

That's it! You have successfully set up your local environment using Pipenv.
