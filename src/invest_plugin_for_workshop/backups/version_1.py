import logging

import numpy
from osgeo import gdal
from osgeo import ogr
import pandas as pd
import pygeoprocessing

from natcap.invest.file_registry import FileRegistry
from natcap.invest import validation
from natcap.invest import gettext
from natcap.invest import spec
from natcap.invest import utils

LOGGER = logging.getLogger(__name__)

MODEL_SPEC = spec.ModelSpec(
    model_id="birb_habitat",
    model_title=gettext("Birb Habitat"),
    module_name=__name__,
    userguide='',
    input_field_order=[[
        'workspace_dir', 'lulc_raster', 'biophysical_table'
    ]],
    inputs=[
        spec.WORKSPACE,
        spec.SingleBandRasterInput(
            id="lulc_raster",
            name="LULC",
            data_type=int,
            about="Land use/land cover raster",
            units=None
        ),
        spec.CSVInput(
            id="biophysical_table",
            name="Biophysical table",
            about=(
                "Table mapping each LULC code to the type of tree cover on that LULC class"),
            columns=[
                spec.IntegerInput(
                    id="lucode",
                    about=(
                        "LULC codes from the LULC raster. Each code must be a unique"
                        " integer."
                    )
                ),
                spec.OptionStringInput(
                    id="tree_type",
                    about=gettext("Type of tree cover on each LULC class"),
                    options=[
                        spec.Option(key="coniferous", description="Predominantly coniferous tree cover"),
                        spec.Option(key="deciduous", description="Predominantly deciduous tree cover"),
                        spec.Option(key="none", description="No tree cover")
                    ]
                ),
            ]
        )
    ],
    outputs=[
        spec.SingleBandRasterOutput(
            id="birb_count_raster",
            path="birb_count.tif",
            about="Map of total number of birbs per pixel",
            data_type=float,
            units=None
        )
    ]
)


def aggregate_results(raster_path, source_vector_path, target_vector_path):
    """Aggregate number of birbs for each AOI polygon.

    Args:
        raster_path (string): path to a raster of birb counts per pixel
        source_vector_path (string): path to the original AOI vector to aggregate over
        target_vector_path (string): path to the target vector, which will be created
            as a copy of the source vector with an added 'number_of_birbs' field

    Returns:
        None
    """
    # make a copy of the source vecotr, reprojected to the raster's projection
    pygeoprocessing.reproject_vector(
        base_vector_path=source_vector_path,
        target_projection_wkt=pygeoprocessing.get_raster_info(
            raster_path)['projection_wkt'],
        target_path=target_vector_path,
        driver_name='GPKG')

    zonal_stats = pygeoprocessing.zonal_statistics(
        base_raster_path_band=(raster_path, 1),
        aggregate_vector_path=target_vector_path,
        ignore_nodata=True)

    dataset = gdal.OpenEx(target_vector_path, gdal.OF_VECTOR | gdal.GA_Update)
    layer = dataset.GetLayer()

    # Add the new field to the vector
    field_defn = ogr.FieldDefn('number_of_birbs', ogr.OFTReal)
    layer.CreateField(field_defn)

    # Iterate over each polygon feature in the vector
    layer.ResetReading()
    for feature in layer:
        fid = feature.GetFID()
        feature.SetField('number_of_birbs', float(zonal_stats[fid]['sum']))
        layer.SetFeature(feature)


def execute(args):
    """Execute the birb model.

    Args:
        args (dict): dictionary mapping input ids to their user-provided values

    Returns:
        file registry dictionary
    """
    args = MODEL_SPEC.preprocess_inputs(args)
    LOGGER.info(args)
    MODEL_SPEC.create_output_directories(args)
    file_registry = FileRegistry(
        outputs=MODEL_SPEC.outputs,
        workspace_dir=args['workspace_dir'])

    # Calculate pixel area in hectares from pixel dimensions in meters
    pixel_height, pixel_width = pygeoprocessing.get_raster_info(
        args['lulc_raster'])['pixel_size']
    pixel_area_ha = abs(pixel_height * pixel_width) / 10000

    # Read in the biophysical table as a pandas dataframe
    biophysical_df = MODEL_SPEC.get_input(
        'biophysical_table').get_validated_dataframe(
        args['biophysical_table'])

    # Convert the dataframe into a dictionary that maps each LULC code
    # to the predominant tree type ('coniferous', 'deciduous', or 'none')
    lucode_to_tree_type = biophysical_df.set_index('lucode')['tree_type'].to_dict()

    # Number of birbs per hectare for each tree type
    tree_type_to_birb_density = {
        'coniferous': 150,
        'deciduous': 250,
        'none': 20
    }

    # Convert the tree type values to the corresponding birb count per pixel
    lucode_to_birb_count = {
        lucode: tree_type_to_birb_density[tree_type] * pixel_area_ha
        for lucode, tree_type in lucode_to_tree_type.items()
    }
    LOGGER.info(lucode_to_birb_count)

    # Reclassify LULC to birb count
    utils.reclassify_raster(
        raster_path_band=(args['lulc_raster'], 1),
        value_map=lucode_to_birb_count,
        target_raster_path=file_registry['birb_count_raster'],
        target_datatype=gdal.GDT_Float32,
        target_nodata=-1,
        error_details={
            'raster_name': 'birb_count_raster',
            'column_name': 'lucode',
            'table_name': 'biophysical_table'
        })

    return file_registry.registry


@validation.invest_validator
def validate(args, limit_to=None):
    return validation.validate(args, MODEL_SPEC)
