from setuptools import setup, find_packages
import setuptools
import subprocess
import os

setup(
    name='domreducer',  # Package name
    version='0.0.4',  # Version of your package
    author='Enes Kuzucu',  # Your name
    
    description='package to reduce DOM data (html or JS) without losing information so it can fit into LLMs. ',  # Short description
    long_description=open('README.md').read(),  # Long description from a README file
    long_description_content_type='text/markdown',  # Type of the long description
    
    packages=find_packages(),  # Automatically find packages in the directory
    install_requires=[ 'python-dotenv' , 'beautifulsoup4' , 'lxml', 'pyyaml', 'tiktoken'],
    classifiers=[
        'Development Status :: 3 - Alpha',  # Development status
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',  # License as you choose
        'Programming Language :: Python :: 3',  # Supported Python versions
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',  # Minimum version requirement of Python
)