# Birb Habitat: A Demo Plugin for the InVEST® Plugin Workshop at the 2026 NatCap Symposium

## Disclaimer: This is Not a Real Scientific Model!
While the Birb Habitat model is loosely inspired by real-world ecosystem services modeling, it is—by design—extraordinarily simple and ignores many important factors that inform whether a particular area might provide suitable habitat for birbs. The numbers used in the model’s calculations are arbitrary and have no basis in reality. In short, this model is not backed by science and should not be used for any serious, real-world modeling.

## About this Plugin
This plugin has been designed as an introduction to InVEST plugin development and should be used exclusively for training workshops or self-paced learning focused on the fundamentals of InVEST plugin development.

Ready to start learning? Follow the [Plugin Workshop Instructions](./INSTRUCTIONS.md).

Looking for examples of InVEST plugins suitable for real-world applications? Check out the [InVEST Plugin Registry](https://natcap.github.io/invest-plugin-registry/plugins/index.html).

## Overview of the Birb Habitat Model
Birbs provide many ecosystem services, including seed dispersal, pollination, pest control, sanitation, soundscape enhancement, and recreation opportunities (e.g., backyard birbing, birbing-related travel). The Birb Habitat model estimates a landscape’s capacity to support birb populations based on tree cover.

## Model Variants
This plugin implements three model variants that highlight different features of InVEST plugin development. The variants are designed to be explored in order, since each variant incrementally builds upon the previous variant.

In the outlines that follow, the 🌱 emoji labels items that are new or different compared to the previous iteration (i.e., 🌱 in Variant 2 indicates a change from Variant 1; 🌱 in Variant 3 indicates a change from Variant 2).

### Variant 1 (Base Model): LULC to Birb Population Raster

#### Inputs
- **Workspace Directory** (text): Directory for storing output files.
- **LULC** (raster, units: None): Land use/land cover raster.
- **Biophysical Table** (CSV): Table mapping each LULC code to the type of tree cover on that LULC class.

  Columns:
  - **lucode** (integer): LULC codes from the LULC raster. Each code must be a unique integer.
  - **tree_type** (option): Type of tree cover on each LULC class.

    Options:
    - `coniferous`: Predominantly coniferous tree cover.
    - `deciduous`: Predominantly deciduous tree cover.
    - `none`: No tree cover.

#### Model
1. Map LULC to tree type raster.
2. Map each `coniferous` pixel to some constant number of birbs, each `deciduous` pixel to some other constant number of birbs, and each `none` pixel to another constant number of birbs. This calculation is based on pixel area and model-defined birbs-per-hectare constants.

#### Outputs
- **birb_count.tif** (raster, units: None): Map of total number of birbs per pixel.

### Variant 2: Add AOI Input and Aggregated Results Output

#### Inputs
- **Workspace Directory** (text): Directory for storing output files.
- **LULC** (raster, units: None): Land use/land cover raster.
- **Biophysical Table** (CSV): Table mapping each LULC code to the type of tree cover on that LULC class.

  Columns:
  - **lucode** (integer): LULC codes from the LULC raster. Each code must be a unique integer.
  - **tree_type** (option): Type of tree cover on each LULC class.

    Options:
    - `coniferous`: Predominantly coniferous tree cover.
    - `deciduous`: Predominantly deciduous tree cover.
    - `none`: No tree cover.
- 🌱 **Area of Interest** (vector): A map of areas over which to aggregate and summarize the final results.

#### Model
1. Map LULC to tree type raster.
2. Map each `coniferous` pixel to some constant number of birbs, each `deciduous` pixel to some other constant number of birbs, and each `none` pixel to another constant number of birbs. This calculation is based on pixel area and model-defined birbs-per-hectare constants.
3. 🌱 Aggregate number of birbs by AOI feature.

#### Outputs
- **birb_count.tif** (raster, units: None): Map of total number of birbs per pixel.
- 🌱 **aggregated_results.gpkg** (vector): Birb density statistics aggregated over each polygon in the Area of Interest vector.

### Variant 3: Add Birb Groups and User-Defined Population Density

#### Inputs
- **Workspace Directory** (text): Directory for storing output files.
- **LULC** (raster, units: None): Land use/land cover raster.
- **Biophysical Table** (CSV): Table mapping each LULC code to the type of tree cover on that LULC class.

  Columns:
  - **lucode** (integer): LULC codes from the LULC raster. Each code must be a unique integer.
  - **tree_type** (option): Type of tree cover on each LULC class.

    Options:
    - `coniferous`: Predominantly coniferous tree cover.
    - `deciduous`: Predominantly deciduous tree cover.
    - `none`: No tree cover.
- **Area of Interest** (vector): A map of areas over which to aggregate and summarize the final results.
- 🌱 **Birb Population Density Table** (CSV): Table mapping user-defined groups of birbs to their population density in coniferous and deciduous forest.

  Columns:
  - **group** (text): User-defined birb type or group (e.g., songbirbs, birbs of prey, hummingbirbs, shorebirbs).
  - **pop_per_ha_coniferous** (number): Population density per hectare of each birb group in coniferous forest.
  - **pop_per_ha_deciduous** (number): Population density per hectare of each birb group in deciduous forest.

#### Model
1. Map LULC to tree type raster.
2. 🌱 Calculate number of birbs in each group per pixel, based on pixel area and birbs-per-hectare values defined in the Birb Population Density Table.
3. 🌱 Calculate total number of birbs (across all groups) per pixel.
4. 🌱 Aggregate number of birbs in each group by AOI feature.

#### Outputs
- **birb_count.tif** (raster, units: None): Map of total number of birbs per pixel.
- 🌱 **aggregated_results.gpkg** (vector): Birb density statistics aggregated over each polygon in the Area of Interest vector and broken down by birb group.
- 🌱 **[GROUP]_count.tif** (raster, units: None): Map of birb group counts per pixel. One raster is created for each birb group defined in the Birb Population Density Table.

## Sample Data
Sample data are provided in this repo for convenience. As with the Birb Habitat model itself, the sample data have been created exclusively for training purposes and should not be used in any serious, real-world modeling.
