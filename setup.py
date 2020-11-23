from setuptools import setup, find_packages


setup(
    name='asteroid_gan_exps',
    version='0.1',
    author='Joris Cosentino',
    author_email='joris.cosentino@inria.fr',
    url="https://github.com/JorisCos/asteroid_gan_exps",
    description='Experiments on GANs using Asteroid',
    license='MIT',
    python_requires='>=3.6',
    install_requires=['soundfile',
                      'pyyaml',
                      'pandas',
                      'numpy',
                      'tqdm',
                      'asteroid',
                      'scipy',
                      'pystoi'
                      ],
    extras_require={
        'tests': ['pytest'],
    },
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)