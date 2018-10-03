from setuptools import find_packages, setup

setup(
    name='sapo',
    version=__import__('sapo').__version__,
    description='Minimalistic Python SOAP server',
    author='Edoardo Nodari',
    author_email='info@nodari.me',
    install_requires=[
        'lxml>=3.6.1',
    ],
    packages=find_packages(),
    include_package_data=True,
    license='MIT',
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.4',
    ],
)
