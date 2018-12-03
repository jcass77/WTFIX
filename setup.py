from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="wtfix",
    version="0.0.1",
    author="John Cass",
    author_email="john.cass77@gmail.com",
    description="A pythonic library for connecting to FIX servers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # TODO: update project URL.
    url="https://github.com/jcass77/",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLV3)",
        "Operating System :: OS Independent",
        "Intended Audience :: Financial and Insurance Industry",
    ],
    keywords="FIX financial information exchange",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    # TODO: link to requirements.txt?
    # install_requires=[],
    python_requires=">=3.6",
    # TODO: update URLs
    # project_urls={  # Optional
    #     "Bug Reports": "https://github.com/pypa/sampleproject/issues",
    #     "Funding": "https://donate.pypi.org",
    #     "Say Thanks!": "http://saythanks.io/to/example",
    #     "Source": "https://github.com/pypa/sampleproject/",
    # },
)
