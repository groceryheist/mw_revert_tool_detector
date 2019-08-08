from setuptools import setup
setup(name="mwcomments",
      version="0.1.4",
      description="Utilities for interpreting comments in edits to mediawiki wikis",
      license="GPL3",
      packages=['mwcomments'],
      package_data={'mwcomments':['resources/wiki_patterns.pickle',"resources/wikimedia_sites.pickle"]},
      author="Nathan TeBlunthuis",
      author_email="nathante@uw.edu",
      keywords=['mediawiki'],
      url='https://github.com/groceryheist/mw_revert_tool_detector',
      install_requires=['mwapi>=0.5.1','lxml>=4.3.0','gitpython>=2.1.11',"python-dateutil>=2.7.3",'wikitextparser>=0.26.1','sortedcontainers>=2.1.0', 'python-dateutil>=2.7.3']
)
