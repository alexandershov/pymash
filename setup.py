import setuptools

setuptools.setup(
    name='pymash',
    version='0.2.7',
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'aioboto3==2.0.1',
        'aiodns==1.1.1',
        'aiohttp==3.0.1',
        'aiohttp-jinja2==0.14.0',
        'aiopg==0.13.1',
        'cchardet==2.1.1',  # faster replacement for chardet, used by aiohttp
        'psycopg2==2.7.3.1',
        'PyGithub==1.35',
        'Pygments==2.2.0',
        'requests==2.18.4',
        'SQLAlchemy==1.1.14',
        'voluptuous==0.10.5',
    ],
    tests_require=[
        'beautifulsoup4==4.6.0',
        'pytest==3.2.2',
        'pytest-aiohttp==0.1.3',
    ],
    package_data={
        '': ['templates/*.html', 'templates/static/*.css'],
    }
)
