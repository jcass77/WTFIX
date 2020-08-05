from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="wtfix",
    version="0.15.2",
    author="John Cass",
    author_email="john.cass77@gmail.com",
    description="The Pythonic Financial Information eXchange (FIX) client for humans.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jcass77/WTFIX",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: AsyncIO",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: OS Independent",
        "Intended Audience :: Financial and Insurance Industry",
    ],
    keywords="FIX financial information exchange",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    install_requires=[
        "python-dotenv>=0.10.3",
        "flask-restful>=0.3.7",
        "requests>=2.22",
        "gunicorn>=19.9",
        "aioredis>=1.3",
    ],
    python_requires=">=3.8",
    project_urls={
        "Bug Reports": "https://github.com/jcass77/WTFIX/issues",
        "Source": "https://github.com/jcass77/WTFIX/",
    },
)
