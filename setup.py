from setuptools import setup
setup(name="mwcomments",
      version="0.0.1",
      description="Utilities for interpreting comments in edits to mediawiki wikis",
      license="GPL3",
      packages=['mwcomments'],
      author="Nathan TeBlunthuis",
      author_email="nathante@uw.edu",
      keywords=['mediawiki'],
      url=['https://github.com/groceryheist/python-mwcomments'],
      install_requires=['mwapi','glob','beautifulsoup4']
)

