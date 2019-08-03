from setuptools import setup
setup(name="mwcomments",
      version="0.1.1",
      description="Utilities for interpreting comments in edits to mediawiki wikis",
      license="GPL3",
      packages=['mwcomments'],
      package_data={'mwcomments':['resources/wiki_patterns.pickle',"resources/wikimedia_sites.pickle"]},
      author="Nathan TeBlunthuis",
      author_email="nathante@uw.edu",
      keywords=['mediawiki'],
      url='https://github.com/groceryheist/mw_revert_tool_detector',
      install_requires=['mwapi','beautifulsoup4','lxml','gitpython',"python-dateutil",'wikitextparser','sortedcontainers', 'python-dateutil']
)
