# Python Protonvpn Vpn Connection

The `proton-vpn-connection` component defines the interface that VPN connection backends should implement.

## Development

Even though our CI pipelines always test and build releases using Linux distribution packages,
you can use pip to set up your development environment.

### Proton package registry

If you didn't do it yet, you'll need to set up our internal package registry.
[Here](https://gitlab.protontech.ch/help/user/packages/pypi_repository/index.md#authenticate-to-access-packages-within-a-group)
you have the documentation on how to do that.

### Virtual environment

You can create the virtual environment and install the rest of dependencies as follows:

```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Tests

You can run the tests with:

```shell
pytest
```
