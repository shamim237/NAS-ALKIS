import geopandas as gpd
import sys

def clean_geometries(gdf):
    # Check and fix invalid geometries
    gdf['geometry'] = gdf['geometry'].buffer(0)  # This can help fix some topology issues
    gdf = gdf[gdf.is_valid]  # Remove invalid geometries
    return gdf

def union_shapefiles(shapefile1, shapefile2, output_shapefile):
    gdf1 = gpd.read_file(shapefile1)
    gdf2 = gpd.read_file(shapefile2)

    # Clean geometries
    gdf1 = clean_geometries(gdf1)
    gdf2 = clean_geometries(gdf2)

    # Perform the union
    union_gdf = gpd.overlay(gdf1, gdf2, how='union')

    # Save the result to a new shapefile
    union_gdf.to_file(output_shapefile)

# Example usage
if __name__ == "__main__":
    shapefile1 = sys.argv[1]
    shapefile2 = sys.argv[2]
    output_shapefile = sys.argv[3]
    union_shapefiles(shapefile1, shapefile2, output_shapefile)