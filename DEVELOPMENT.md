# Development instructions

## Development environment setup

- Create a virtual environment: `python -m venv .venv --system-site-packages`
  - For Windows use `<osgeo>/apps/Python39/python.exe` (this requires some dll+pth patching, see [OSGeo4W issue])
- Activate virtual env and install requirements: `pip install -r requirements.txt --no-deps --only-binary=:all:`
  - `pip-sync requirements.txt` can be used if `pip-tools` is installed
- Run tests: `pytest`
- For testing in QGIS, copy `env.example` as `.env` and set variables as needed. Start QGIS using command `qgis-plugin-dev-tools start` or `qpdt s` (with virtual env activated).
- Development tools for testing dock widget with a JSON file is found from Plugins-menu

## Requirements changes

This project uses `pip-tools`. To update requirements, do `python -m pip install pip-tools`, change `requirements.in` and use `pip-compile requirements.in` to generate new `requirements.txt` with fixed versions.

## Code style

Included `.code-workspace` has necessary options set (linting, formatting, tests, extensions) set for VS Code.

Verify code style with `pre-commit run --all-files`, or use `pre-commit install` to generate an actual git hook.

## Commit message style

Commit messages should follow [Conventional Commits notation](https://www.conventionalcommits.org/en/v1.0.0/#summary). Use `pre-commit install --hook-type commit-msg` to generate a git hook for checking commit messages.

## Tests

Run all tests against containerized QGIS environment by:

```bash
docker build . -t qgis-quality-result-gui
docker run --rm -it qgis-quality-result-gui
```

Or run specific tests with:

```bash
docker run --rm -it qgis-quality-result-gui pytest test/unit/quality_result_gui/test_quality_data_fetcher.py
```

## Translations

To update or add translations with the wanted language, run the following in the root of the project:

```bash
(.venv) python tools/update-translations.py src/quality_result_gui src/quality_result_gui/resources/i18n <locale>
```

You can then open the *.ts* files you wish to translate with Qt Linguist and make the changes.

Compile the translations to *.qm* files with *File -> Release*

## Release steps

When the branch is in a releasable state, trigger the `Create draft release` workflow from GitHub Actions. Pass the to-be-released version number as an input to the workflow.

Workflow creates two commits in the target branch, one with the release state and one with the post-release state. It also creates a draft release from the release state commit with auto-generated release notes. Check the draft release notes and modify those if needed. After the release is published, the tag will be created, release workflow will be triggered, and it publishes a new version to PyPI.

Note: if you created the release commits to a non-`main` branch (i.e. to a branch with an open pull request), only publish the release after the pull request has been merged to main branch. Change the commit hash on the draft release to point to the actual rebased commit on the main branch, instead of the now obsolete commit on the original branch. If the GUI dropdown selection won't show the new main branch commits, the release may need to be re-created manually to allow selecting the rebased commit hash.

[OSGeo4W issue]: https://trac.osgeo.org/osgeo4w/ticket/692
