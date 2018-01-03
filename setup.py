import setuptools

setuptools.setup(
    name='pymash',
    version='0.1.0',
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'aiohttp==2.2.5',
        'aiohttp-jinja2==0.14.0',
        'aiodns==1.1.1',
        'aiopg==0.13.1',
        # TODO(aershov182): do we need astroid & cchardet?
        'astroid==1.5.3',
        'cchardet==2.1.1',
        'voluptuous==0.10.5',
        'psycopg2==2.7.3.1',
        'SQLAlchemy==1.1.14',
    ],
    tests_require=[
        'pytest==3.2.2',
        'pytest-aiohttp==0.1.3',
    ]
)
