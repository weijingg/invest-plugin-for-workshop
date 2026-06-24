# import the necessary model attributes from the submodule to the package level
# so that the attributes are exposed on the `invest_demo_plugin` package
from .plugin import MODEL_SPEC
from .plugin import execute
from .plugin import validate
