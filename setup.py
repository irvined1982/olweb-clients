#!/usr/bin/env python
# Copyright 2014 David Irvine
#
# This file is part of olwclients
#
# olwclients is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or (at
# your option) any later version.
#
# olwclients is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with olwclients. If not, see <http://www.gnu.org/licenses/>.

import os
from setuptools import setup


setup(
		name = "OpenlavaWeb clients",
		version = "0.0.1",
		author = "David Irvine",
		author_email = "irvined@gmail.com.com",
		description = ("An demonstration of how to create, document, and publish "
								                                   "to the cheese shop a5 pypi.org."),
							    license = "BSD",
								    keywords = "example documentation tutorial",
									    url = "http://packages.python.org/an_example_pypi_project",
										    packages=['an_example_pypi_project', 'tests'],
											    long_description=read('README'),
												    classifiers=[
														        "Development Status :: 3 - Alpha",
																        "Topic :: Utilities",
																		        "License :: OSI Approved :: BSD License",
																				    ],
													)

