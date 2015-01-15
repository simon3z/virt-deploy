from setuptools import setup, find_packages

setup(
    name="virtdeploy",
    version="0.1.3",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'virt-deploy = virtdeploy.cli:main',
        ]
    },
)
