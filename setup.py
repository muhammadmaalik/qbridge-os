from setuptools import setup, find_packages

setup(
    name="qbridge",
    version="1.0.0",
    description="The Universal Quantum Developer Toolkit (Cybersecurity, ML, Robotics, Chemistry)",
    author="Bitcamp Quantum Team",
    packages=find_packages(),
    install_requires=[
        "qiskit",
        "qiskit-aer",
        "matplotlib",
        "numpy"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Physics",
    ],
)
