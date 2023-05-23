# CHANGELOG

## [1.1.6] - 2023-05-23

- Feat: Add functionality to display quality error feature type and attribute names from layer aliases.

## [1.1.5] - 2023-03-29

- Fix: Do not zoom to error when geometry is null geometry

## [1.1.4] - 2023-03-08

- Fix: Show correct error count when errors are filtered
- Fix: Remove selected error visualization from map when error is removed from list

## [1.1.3] - 2023-03-03

- Feat: Add method to hide dock widget and functionality to recreate error visualizations

## [1.1.2] - 2023-03-01

- Fix: Do not hide filter menu when a filter is selected
- Fix: Fix missing marker symbol from line type annotations
- Feat: Allow configuring quality layer styles
- Feat: Add keyboard shortcut for visualize errors on map

## [1.1.1] - 2023-02-23

- Feat: Change Show user processed filter into checkbox selection

## [1.1.0] - 2023-02-16

- Feat: Add optional extra info field to quality error. Extra info is displayed in the tooltip of error description and may contain html formatted text.
- Refactor: Remove language specific description fields from quality error and include only a single field for description.

## [1.0.0] - 2023-02-14

- Feat: Added an API to add custom filters for errors.
- Fix: Hide empty branches from quality error list when user processed errors are hidden and user processes all errors for a feature
- Fix: Error layer stays visible after minimizing QGIS.

## [0.0.4] - 2022-12-28

- Feat: Emit mouse event signal for selected error feature
- Feat: New filter to filter quality errors by error attribute value
- Feat: Add tooltip for quality error description
- Feat: Update data in tree view partially when data changes
- Fix: Minor styling fixes of tree view
- Fix: Visualize error when description is clicked

## [0.0.3] - 2022-12-15

- Fix: Use glob paths for missing build resource files

## [0.0.2] - 2022-12-14

- Fix: Fix missing ui and svg files by including them in setuptools build

## [0.0.1] - 2022-12-14

- Initial release: QGIS dock widget for visualizing quality check results

[0.0.1]: https://github.com/nlsfi/quality-result-gui/releases/tag/v0.0.1
[0.0.2]: https://github.com/nlsfi/quality-result-gui/releases/tag/v0.0.2
[0.0.3]: https://github.com/nlsfi/quality-result-gui/releases/tag/v0.0.3
[0.0.4]: https://github.com/nlsfi/quality-result-gui/releases/tag/v0.0.4
[1.0.0]: https://github.com/nlsfi/quality-result-gui/releases/tag/v1.0.0
[1.1.0]: https://github.com/nlsfi/quality-result-gui/releases/tag/v1.1.0
[1.1.1]: https://github.com/nlsfi/quality-result-gui/releases/tag/v1.1.1
[1.1.2]: https://github.com/nlsfi/quality-result-gui/releases/tag/v1.1.2
[1.1.3]: https://github.com/nlsfi/quality-result-gui/releases/tag/v1.1.3
[1.1.4]: https://github.com/nlsfi/quality-result-gui/releases/tag/v1.1.4
[1.1.5]: https://github.com/nlsfi/quality-result-gui/releases/tag/v1.1.5
[1.1.6]: https://github.com/nlsfi/quality-result-gui/releases/tag/v1.1.6
