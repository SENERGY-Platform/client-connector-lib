import setuptools

def read_version():
    values = dict()
    with open('connector/__init__.py', 'r') as init_file:
        exec(init_file.read(), values)
    return values.get('__version__')

def read_readme():
    with open("README.md", "r") as readme_file:
        readme = readme_file.read()
    return readme

setuptools.setup(
    name='sepl-connector-client',
    version=read_version(),
    author='Yann Dumont',
    author_email='dumont@infai.org',
    description='Framework for users wanting to integrate their personal IoT project / device with the SEPL platform.',
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url='https://gitlab.wifa.uni-leipzig.de/fg-seits/connector-client',
    packages=setuptools.find_packages(),
    install_requires=['websockets'],
    python_requires='>=3.5.3',
    classifiers=(
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers',
        'Operating System :: Unix',
        'Natural Language :: English',
    ),
)