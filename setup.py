import os.path

import setuptools

root_dir = os.path.abspath(os.path.dirname(__file__))

description = "A Python wrapper for the HubSpot contacts and contact properties API"

with open(os.path.join(root_dir, 'README.md')) as f:
    long_description = f.read()

setuptools.setup(
    name='hubbypy',
    version='0.1.3',
    description=description,
    long_description=long_description,
    url='https://github.com/gojefferson/hubbypy',
    author='Jeff Kerr',
    author_email='jeff@casefleet.com',
    license='BSD',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    py_modules=[
        'hubbypy.contact_properties',
        'hubbypy.hub_api',
    ],
    install_requires=[
        'requests',
    ],
)
