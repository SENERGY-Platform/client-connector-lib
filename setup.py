"""
   Copyright 2018 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import setuptools

def read_version():
    values = dict()
    with open('connector_lib/__init__.py', 'r') as init_file:
        exec(init_file.read(), values)
    return values.get('__version__')

setuptools.setup(
    name='client-connector-lib',
    version=read_version(),
    author='Yann Dumont',
    description='Library for users wanting to integrate their personal IoT project / device with the SEPL platform.',
    license='Apache License 2.0',
    url='https://github.com/SENERGY-Platform',
    packages=setuptools.find_packages(),
    install_requires=['websockets>=5,<8'],
    python_requires='>=3.5.3',
    classifiers=(
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Intended Audience :: Developers',
        'Operating System :: Unix',
        'Natural Language :: English',
    ),
)
