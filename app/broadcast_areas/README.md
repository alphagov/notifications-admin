# Broadcast areas data

## Adding or updating source files

If the files are in GeoJSON format you can drop them straight in.

If you have a Shapefile, for example from the [ONS Open Geography Portal](https://geoportal.statistics.gov.uk/), you need to convert it:
- download the .zip from the portal
- extract it, giving you a folder with a few files in
- go to https://mapshaper.org
- drag all the files in the folder into mapshaper
- click ‘import’
- you should see a rendering of the shapes
- click ‘console’ (top right)
- run this command: `mapshaper -proj wgs84`
- click ‘export’ (top right)
- choose ‘GeoJSON’
- click the button
- done

## Creating or updating the broadcast areas database

There is a script to generate the broadcast areas database, so you should run

```
./app/broadcast_areas/create-broadcast-areas-db.py
```
