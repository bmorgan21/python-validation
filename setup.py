from distutils.core import setup

setup(
    name='validation21',
    packages=['validation21'],
    version='0.2.4',
    description='Validation library for Python.',
    author='Brian S Morgan',
    author_email='brian.s.morgan@gmail.com',
    url='https://github.com/bmorgan21/python-validation',
    install_requires=[
        'enum21>=0.2.0',
        'python-dateutil'
    ],
)
