Creating releases
=================

#. Update changelog and commit it.

#. Bump the version number in ``setup.py``.

#. Merge the release branch (``develop`` in the example) into master::

    git checkout master
    git merge --no-ff -m "Release v0.0.1" develop

#. Install/upgrade tools used for packaging::

    pip install -U twine wheel

#. Build package and test it manually in a new virtualenv. The following assumes the use of virtualenvwrapper::

    python setup.py sdist bdist_wheel

    mktmpenv
    pip install path/to/dist/wtfix-0.0.1.tar.gz
    toggleglobalsitepackages
    # do manual test
    deactivate

    mktmpenv
    pip install path/to/dist/wtfix-0.0.1-py3-none-any.whl
    toggleglobalsitepackages
    # do manual test
    deactivate

#. Tag the release::

    git tag -a -m "Release v0.0.1" v0.0.1

#. Push to GitHub::

    git push --follow-tags

#. Upload the previously built and tested sdist and bdist_wheel packages to PyPI::

    twine upload dist/wtfix-0.0.1*

#. Merge ``master`` back into ``develop`` and push the branch to GitHub.

#. Document the release on GitHub.
