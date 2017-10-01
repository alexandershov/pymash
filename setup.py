import setuptools

setuptools.setup(
    name='pymash',
    version='0.1.0',
    packages=setuptools.find_packages(),
    install_requires=[
        'aiohttp==2.2.5',
        'aiodns==1.1.1',
        'cchardet==2.1.1',
        'psycopg2==2.7.3.1',
        'SQLAlchemy==1.1.14',
    ],
    tests_require=[
        'pytest==3.2.2'
    ]
)
