#!/usr/bin/env python3
import setuptools
from vk_dump_extractor import __version__


def load_requirements():
    with open('requirements.txt') as f:
        return f.read().splitlines()


setuptools.setup(
    name='vk-dump-extractor',
    version=__version__,
    zip_safe=False,
    include_package_data=True,
    install_requires=load_requirements(),
    packages=setuptools.find_packages(),
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'vk-dump-extractor=vk_dump_extractor.__main__:main',
        ]
    },
)
