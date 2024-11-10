# eLxr Metrics Doc

## Generate API doc

Steps to generate eLxr Metrics API document:

```bash
cd docs
pip install -r requirements.txt
mkdir -p _static
mkdir -p _templates
make html
```

After `make`, the newly generated API doc can be viewed at [\_build/html/index.html](_build/html/index.html).

## Rebuild API doc

After some code changes and to rebuild the HTML, go to the `docs` folder and run:

```bash
make clean html
make html
```

This will rebuild your HTMLs while taking into consideration code changes.

## Note

The initial `docs` contents were generated via the following steps:

```bash
pushd docs
pip install -r requirements.txt
sphinx-quickstart
popd
sphinx-apidoc -o docs  src/elxr_metrics/
```

## Reference

- [Python Package Template](https://github.com/microsoft/python-package-template)
- [Documenting Python code with Sphinx](https://towardsdatascience.com/documenting-python-code-with-sphinx-554e1d6c4f6d)
- [Automatic API Documentation](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#ext-autodoc)
