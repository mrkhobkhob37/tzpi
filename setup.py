'''
tzpi setup script (fork of pytz 2024.1; distribution + import renamed).
'''

import tzpi
import os
import os.path

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

me = 'Stuart Bishop'
memail = 'stuart@stuartbishop.net'
packages = ['tzpi', 'tzpi.tests']
resources = ['zone.tab']
for dirpath, dirnames, filenames in os.walk(os.path.join('tzpi', 'zoneinfo')):
    # remove the 'tzpi' part of the path
    basepath = dirpath.split(os.sep, 1)[1]
    resources.extend([os.path.join(basepath, filename) for filename in filenames])
package_data = {'tzpi': resources + ['README.rst']}

assert len(resources) > 10, 'zoneinfo files not found!'

setup(
    name='tzpi',
    version=tzpi.FORK_VERSION,
    zip_safe=True,
    description='World timezone definitions, modern and historical',
    long_description=open('README.rst', 'r').read(),
    author=me,
    author_email=memail,
    maintainer=me,
    maintainer_email=memail,
    url='http://pythonhosted.org/pytz',
    license='MIT',
    keywords=['timezone', 'tzinfo', 'datetime', 'olson', 'time'],
    packages=packages,
    package_data=package_data,
    platforms=['Independent'],
    classifiers=[
        'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
