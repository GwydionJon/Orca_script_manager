# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))
print(os.path.abspath("../.."))


project = "script_maker2000"
copyright = "2024, Gwydion Daskalakis, Manuel Schmitt"
author = "Gwydion Daskalakis, Manuel Schmitt"
release = "2024"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "myst_parser",
    "sphinx_rtd_theme",
    "sphinx_click",
    "sphinx_copybutton",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# Make sure that classes are documented by their init method
autoclass_content = "init"

# This is an extension that allows us to preserve the default arguments of functions
# as written in code without evaluating them.
autodoc_preserve_defaults = True

# This is kind of unfortunate, but we get errors that are specific to the documentation build:
nbsphinx_allow_errors = True


# Configure sphinx_copybutton to select both block and inline code
copybutton_selector = 'div.highlight pre, div.literal-block pre, p code'  