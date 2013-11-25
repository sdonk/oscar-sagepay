#!/usr/bin/env python
from setuptools import setup, find_packages

from source.sagepay import VERSION


MIN_OSCAR_VERSION = (0, 5)
try:
    import oscar
except ImportError:
    # Oscar not installed
    pass
else:
    # Oscar is installed, assert version is up-to-date
    if oscar.VERSION < MIN_OSCAR_VERSION:
        raise ValueError(
            "Oscar>%s required, current version: %s" % (
                ".".join(MIN_OSCAR_VERSION), oscar.get_version()))


setup(name='oscar-sagepay',
      version=VERSION,
      url='https://github.com/sdonk/django-oscar-sagepay',
      author="Alessandro De Noia",
      author_email="alessandro.denoia@gmail.com",
      description="SagePay payment module for django-oscar",
      long_description=open('../django-oscar-sagepay/README.rst').read(),
      keywords="Payment, SagePay, Oscar",
      license=open('../django-oscar-sagepay/LICENSE').read(),
      platforms=['linux'],
      packages=find_packages(exclude=['tests*']),
      include_package_data=True,
      # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Web Environment',
          'Framework :: Django',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Operating System :: Unix',
          'Programming Language :: Python',
          'Topic :: Other/Nonlisted Topic'],
      install_requires=[
          'requests>=2.0',
          'django-oscar==0.5.1'],
      )
