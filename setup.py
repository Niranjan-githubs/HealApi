from setuptools import setup, find_packages

setup(
    name="healapi",
    version="0.1.0",
    description="Self-Healing API Test Automation System",
    author="Niranjan C",
    author_email="niranjanlite@gmail.com",  # <-- Add your email here
    packages=find_packages(),
    install_requires=[
        "pyyaml",
        "jsonschema",
        "requests",
        "typer",
        # Add other dependencies from requirements.txt
    ],
    entry_points={
        "console_scripts": [
            "healapi=healapi.cli:main"
        ]
    },
    python_requires=">=3.7",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
