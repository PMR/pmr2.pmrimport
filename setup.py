from setuptools import setup, find_packages
import os

version = '0.0'
scripts = [
    'pmr2_pmrextract',
    'pmr2_mkhg',
]

setup(name='pmr2.pmrimport',
      version=version,
      description="PMR data import module for PMR2",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='Tommy Yu',
      author_email='tommy.yu@auckland.ac.nz',
      url='',
      license='GPL',
      scripts=scripts,
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['pmr2'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'lxml>=2.1.0',
          'mercurial>=1,<1.1',
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
