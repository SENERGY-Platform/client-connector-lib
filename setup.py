"""
   Copyright 2019 InfAI (CC SES)

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

def read_metadata():
    values = dict()
    with open('cc_lib/__init__.py', 'r') as init_file:
        exec(init_file.read(), values)
    metadata = {key: value for key, value in values.items() if key.startswith('__')}
    return metadata

metadata = read_metadata()

setuptools.setup(
    name=metadata.get('__title__'),
    version=metadata.get('__version__'),
    author=metadata.get('__author__'),
    description=metadata.get('__description__'),
    license=metadata.get('__license__'),
    url=metadata.get('__url__'),
    copyright=metadata.get('__copyright__'),
    packages=setuptools.find_packages(),
    install_requires=['websockets>=5,<8', 'paho-mqtt'],
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
