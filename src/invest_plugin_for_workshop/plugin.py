import logging

import numpy
from osgeo import gdal
from osgeo import ogr
import pygeoprocessing

from natcap.invest.file_registry import FileRegistry
from natcap.invest.unit_registry import u
from natcap.invest import validation
from natcap.invest import spec
from natcap.invest import utils

LOGGER = logging.getLogger(__name__)
_model_description = (
    """
    Birbs provide many ecosystem services, including seed dispersal,
    pollination, pest control, sanitation, soundscape enhancement, and
    recreation opportunities (e.g., backyard birbing, birbing-related travel).
    The Birb Habitat model estimates a landscape's capacity to support birb
    populations based on tree cover. While the Birb Habitat model is loosely
    inspired by real-world ecosystem services modeling, it is not backed by
    science and should not be used for any serious, real-world modeling.
    """
)

MODEL_SPEC = spec.ModelSpec(
    model_id="birb_habitat",
    model_title="Birb Habitat",
    module_name=__name__,
    about=_model_description,
    reporter="invest_plugin_for_workshop.reporter",
    userguide='https://github.com/natcap/invest-plugin-for-workshop/blob/main/README.md',
    input_field_order=[[
        'workspace_dir', 'lulc_raster', 'biophysical_table',
        # 'aoi_path',  # Uncomment for Version 2
        # 'birb_population_density_table'  # Uncomment for Version 3
    ]],
    inputs=[
        spec.WORKSPACE,
        spec.SingleBandRasterInput(
            id="lulc_raster",
            name="LULC",
            data_type=int,
            about="Land use/land cover raster.",
            units=None
        ),
        spec.CSVInput(
            id="biophysical_table",
            name="Biophysical table",
            about=(
                "Table mapping each LULC code to the type of tree cover on that LULC class."),
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
                    about="Type of tree cover on each LULC class.",
                    options=[
                        spec.Option(key="coniferous", about="Predominantly coniferous tree cover."),
                        spec.Option(key="deciduous", about="Predominantly deciduous tree cover."),
                        spec.Option(key="none", about="No tree cover.")
                    ]
                ),
            ]
        ),

        # ########## Uncomment for Version 2 ##################################
        # spec.VectorInput(
        #     id="aoi_path",
        #     name="area of interest",
        #     about=(
        #         "A map of areas over which to aggregate and summarize the final results."
        #     ),
        #     geometry_types={"POLYGON", "MULTIPOLYGON"},
        #     fields=[]
        # ),
        #######################################################################

        # ########## Uncomment for Version 3 ##################################
        # spec.CSVInput(
        #     id="birb_population_density_table",
        #     name="Birb population density table",
        #     about=(
        #         "Table mapping user-defined groups of birbs to their population density in "
        #         "coniferous and deciduous forest."),
        #     columns=[
        #         spec.StringInput(
        #             id="group",
        #             about="User-defined birb type or group."
        #         ),
        #         spec.NumberInput(
        #             id="pop_per_ha_coniferous",
        #             about=(
        #                 "Population density per hectare of each birb group in coniferous forest."),
        #             units=None
        #         ),
        #         spec.NumberInput(
        #             id="pop_per_ha_deciduous",
        #             about=(
        #                 "Population density per hectare of each birb group in deciduous forest."),
        #             units=None
        #         )
        #     ]
        # )
        #######################################################################

    ],
    outputs=[
        spec.SingleBandRasterOutput(
            id="birb_count_raster",
            path="birb_count.tif",
            about="Map of total number of birbs per pixel.",
            data_type=float,
            units=u.none
        ),

        # ############ Uncomment for Version 2 ################################
        # spec.VectorOutput(
        #     id="aggregated_results_vector",
        #     path="aggregated_results.gpkg",
        #     about=(
        #         "Birb density statistics aggregated over each polygon "
        #         "in the area of interest vector."),
        #     fields=[spec.NumberOutput(
        #         id="number_of_birbs",
        #         about="Total number of birbs projected to exist in each polygon.",
        #         units=u.none
        #     )]
        # ),
        #######################################################################

        # ############# Uncomment for Version 3 ###############################
        # spec.SingleBandRasterOutput(
        #     id="[GROUP]_count_raster",
        #     path="[GROUP]_count.tif",
        #     about="Map of birb group counts per pixel.",
        #     data_type=float,
        #     units=u.none
        # )
        #######################################################################

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
    # make a copy of the source vector, reprojected to the raster's projection
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


    # ############# Uncomment for Version 3 ###################################
    # # Read in the birb population density table as a pandas dataframe
    # birb_population_density_df = MODEL_SPEC.get_input(
    #     'birb_population_density_table').get_validated_dataframe(
    #     args['birb_population_density_table']).set_index('group')

    # birb_group_count_rasters = []
    # for group, density_values in birb_population_density_df.iterrows():
    #     # Build a dictionary that maps the group name to its population
    #     # density in each tree cover type
    #     density_dict = {
    #         'none': 0,
    #         'coniferous': density_values['pop_per_ha_coniferous'],
    #         'deciduous': density_values['pop_per_ha_deciduous']
    #     }

    #     # Build a dictionary that maps each lucode to the number of birbs of
    #     # this group per pixel in that LULC class
    #     value_map = {
    #         lucode: density_dict[lucode_to_tree_type[lucode]] * pixel_area_ha
    #         for lucode in lucode_to_tree_type.keys()
    #     }
    #     # Reclassify LULC to birb density using the table
    #     utils.reclassify_raster(
    #         raster_path_band=(args['lulc_raster'], 1),
    #         value_map=value_map,
    #         target_raster_path=file_registry['[GROUP]_count_raster', group],
    #         target_datatype=gdal.GDT_Float32,
    #         target_nodata=-1,
    #         error_details={
    #             'raster_name': 'lulc_raster',
    #             'column_name': 'lucode',
    #             'table_name': 'biophysical_table'
    #         })
    #     birb_group_count_rasters.append(file_registry['[GROUP]_count_raster', group])

    # # Sum up the birb group count rasters to get a total birb count raster
    # pygeoprocessing.raster_map(
    #     op=lambda *xs: numpy.sum(xs, axis=0),
    #     rasters=birb_group_count_rasters,
    #     target_path=file_registry['birb_count_raster'],
    #     target_nodata=-1,
    #     target_dtype=float)
    ###########################################################################

    # ############# Uncomment for Version 2 ###################################
    # # Aggregate by AOI geometries
    # aggregate_results(
    #     raster_path=file_registry['birb_count_raster'],
    #     source_vector_path=args['aoi_path'],
    #     target_vector_path=file_registry['aggregated_results_vector'])
    ###########################################################################

    return file_registry.registry


@validation.invest_validator
def validate(args, limit_to=None):
    return validation.validate(args, MODEL_SPEC)
