from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp-freshbooks-blockchain",
    version="0.1.0",
    author="Jordan Ehrig & Claude",
    author_email="jordan@samuraibuddha.com",
    description="Blockchain-powered Freshbooks accounting MCP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SamuraiBuddha/mcp-freshbooks-blockchain",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Financial :: Accounting",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "mcp>=1.0.0",
        "requests>=2.31.0",
        "requests-oauthlib>=1.3.1",
        "web3>=6.11.0",
        "pydantic>=2.4.0",
        "python-dotenv>=1.0.0",
        "cryptography>=41.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-freshbooks-blockchain=mcp_freshbooks_blockchain.server:main",
        ],
    },
)