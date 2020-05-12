from setuptools import find_packages
from setuptools import setup

__author__ = 'Ebben Aries <exa@arrcus.com>'
__license__ = ''

req_lines = [line.strip() for line in open("requirements.txt").readlines()]
install_reqs = list(filter(None, req_lines))

setup(
        name='python-arcapi',
        version='0.4.2',
        author=__author__,
        packages=find_packages('.'),
        install_requires=install_reqs,
        platforms=['Posix'],
        keywords=('Arrcus', 'ArcOS'),
        python_requires='>=2.7',
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT Licence',
            'Programming Language :: Python :: 2.7']
        )

