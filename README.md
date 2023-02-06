# quality-result-gui

QGIS plugin for visualizing quality check results.

## Plugin

Not implemented yet.

## Library

To use this library as an external dependency in your plugin or other Python code, install it using `pip install quality-result-gui` and use imports from the provided `quality_result_gui` package. If used in a plugin, library must be installed in the runtime QGIS environment or use [qgis-plugin-dev-tools] to bundle your plugin with runtime dependencies included.

### Minimal working example (with JSON file)

For quality dock widget to work, a subclass of QualityResultClient needs to be first implemented. Instance of the created API client class is then passed to QualityErrorsDockWidget. For a real-world application, a separate backend application is needed for checking data quality and provide the quality check results for the QGIS plugin.

Example of the expected api response can be seen in [this file](./src/quality_result_gui_plugin/dev_tools/example_quality_errors/quality_errors.json). [Example parser class](./src/quality_result_gui_plugin/dev_tools/example_quality_errors/quality_errors.json) for json response is also provided for the following example to work:

```python
import json

from qgis.utils import iface

from quality_result_gui.api.quality_api_client import QualityResultClient
from quality_result_gui.api.types.quality_error import QualityErrorsByPriority
from quality_result_gui_plugin.dev_tools.response_parser import QualityErrorResponse
from quality_result_gui.quality_error_manager import QualityResultManager


class ExampleQualityResultClient(QualityResultClient):

    def get_results(self) -> Optional[List[QualityErrorsByPriority]]:
        """
        Retrieve latest quality errors from API

        Returns:
            None: if no results available
            List[QualityErrorsByPriority]: if results available

        Raises:
            QualityResultClientError: if request fails
            QualityResultServerError: if check failed in backend
        """
        full_path_to_json = "some-path/example_quality_errors.json"
        example_response = json.loads(Path(full_path_to_json).read_text())

        return QualityErrorResponse(example_response).errors_by_priority

    def get_crs(self) -> QgsCoordinateReferenceSystem:
        return QgsCoordinateReferenceSystem("EPSG:3067")



api_client = ExampleQualityResultClient()
quality_manager = QualityResultManager(api_client, iface.mainWindow())
quality_manager.show_dock_widget()

```

## Development of quality-result-gui

See [development readme](./DEVELOPMENT.md).

## License & copyright

Licensed under GNU GPL v3.0.

This tool is part of the topographic data production system developed in National Land Survey of Finland. For further information, see:

- [Abstract for FOSS4G](https://talks.osgeo.org/foss4g-2022/talk/TDDGJ9/)
- [General news article about the project](https://www.maanmittauslaitos.fi/en/topical_issues/topographic-data-production-system-upgraded-using-open-source-solutions)

Contact details: eero.hietanen@maanmittauslaitos.fi

Copyright (C) 2022 [National Land Survey of Finland].

[National Land Survey of Finland]: https://www.maanmittauslaitos.fi/en
[qgis-plugin-dev-tools]: https://github.com/nlsfi/qgis-plugin-dev-tools
