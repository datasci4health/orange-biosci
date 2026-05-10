# setup.py
from setuptools import setup, find_packages

NAME = 'orange-biosci'
VERSION = '0.9.0'
DESCRIPTION = 'Custom Orange Bio Sci Widgets'
AUTHOR = 'André Santanchè'
URL = 'https://github.com/datasci4health/orange-biosci'
LICENSE = 'LGPL-2.1-or-later'

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    url=URL,
    license=LICENSE,
    packages=find_packages(),
    package_data={
        # Include any icons or other resources
        'orange3biosci': ['icons/*.svg', 'icons/*.png'],
    },
    include_package_data=True,
    entry_points={
        'orange3.addon': (
            'mywidgets = orange3biosci',
        ),
        'orange.widgets': (
            'My Custom Widgets = orange3biosci.widgets',
        ),
    },
    install_requires=[
        'orange3>=3.32.0',
        "pandas",
        "numpy",
        "lxml"
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Scientific/Engineering :: Information Analysis'
    ],
    keywords=[
        'orange3',
        'bioinformatics',
        'geo',
        'gene expression'
    ],
)
