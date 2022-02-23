# Open ICGC plugin

QGIS Plugin for accessing [open data](https://www.icgc.cat/en/The-ICGC/Public-Information/Transparency/Re-use-of-the-information) published by the [ICGC](https://www.icgc.cat/en) (Institut Cartogràfic de Catalunya, Catalan Mapping Agency).

It provides geocoding searches for place names, streets, roads, coordinates in different reference systems:

![geofinder](docs/images/geo_finder.png)

loading of base data layers:

![resources](docs/images/resources.png)

time series management:

![time_series](docs/images/time_series.png)

search of historic raster photograms:

![photo_search](docs/images/photo_search.png)

downloading of vectorial o raster information by area, municipality or county (depending on the product):

![downloads](docs/images/downloads.png)

basic style control:

![styles](docs/images/styles.png)

and show help:

![help](docs/images/help.png)

More data and services will be added in the near future.

This plugin uses [suds-py3](https://pypi.org/project/suds-py3/), [wsse](https://gist.github.com/copitux/5029872) libraries and spanish land registry [geo services](https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCoordenadas.asmx?wsdl)
