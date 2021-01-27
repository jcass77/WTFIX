## Creating releases

1. Update changelog and commit it.

2. Bump the version number in ``setup.py`` and commit it.

3. Merge the release branch (``develop`` in the example) into ``master``:

    ```
    git checkout master
    git merge --no-ff -m "Release v0.0.1" develop
    ```

4. Install / upgrade tools used for packaging:

    ```
    pip install -U twine wheel
    ```

5. Build package:

    ```
    python setup.py sdist bdist_wheel
    ```

6. Tag the release:

    ```
    git tag -a -m "Release v0.0.1" v0.0.1
    ```

7. Push to GitHub:

    ```
    git push --follow-tags
    ```

8. Upload the previously built and tested sdist and bdist_wheel packages to PyPI:

    ```
    twine upload dist/wtfix-0.0.1*
    ```

9. Merge ``master`` back into ``develop`` and push the branch to GitHub.

10. Document the release on GitHub.
