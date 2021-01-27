## Creating releases

1. Update changelog and commit it.

2. Bump the version number in ``setup.py`` and commit it.

3. Merge the release branch (``develop`` in the example) into ``master``:

    ```
    git checkout master
    git merge --no-ff -m "Release v0.0.1" develop
    ```

4. Tag the release:

    ```
    git tag -a -m "Release v0.0.1" v0.0.1
    ```

5. Push to GitHub:

    ```
    git push --follow-tags
    ```

6. Merge ``master`` back into ``develop`` and push the branch to GitHub.

7. Document the release on GitHub. The 'Upload Python package' GitHub action should automatically publish the release
to PyPI.
