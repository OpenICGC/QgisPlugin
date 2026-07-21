rem Compiling plugin and dialog resources
rem pyrcc5 -o resources_rc.py resources.qrc
rem pyrcc5 -o qlib3\base\resources_rc.py qlib3\base\resources.qrc
rem pyrcc5 -o qlib3\geofinderdialog\resources_rc.py qlib3\geofinderdialog\resources.qrc
rem pyrcc5 -o qlib3\photosearchselectiondialog\resources_rc.py qlib3\photosearchselectiondialog\resources.qrc

rem Compiling language files (ts -> qm interactively)
linguist i18n\openicgc_ca.ts
linguist i18n\openicgc_es.ts
