# %%
import pandas as pd #like tidyverse & dplyr in R
import sqlalchemy as sa
import requests
import io
import psycopg2
import numpy as np #for log-log transformation dealing with skewed vars & also reverse the log transformation back to normal

#EXTRACT
    #first connect to PostgreSQL database
DATA_URL = "postgresql+psycopg2://postgres:uncutnails@localhost:5432/Building_Permits_KW"
engine = sa.create_engine(DATA_URL)

    #fix pagination
records = []
offset = 0
batch_size = 2000  #ArcGIS server enforces a maximum limit of 2,000 rows per individual request
fetching = True

    #historical data extraction loop
while fetching:
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "json",               #json unlocks pagination limits
        "resultRecordCount": batch_size,
        "resultOffset": offset,
        "sqlFormat": "standard"
    }


    #fetch data from live api
    api_url = "https://services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/Building_Permits/FeatureServer/0/query"
    response = requests.get(api_url, params=params)
    if response.status_code == 200: #if request was successful/HTTP-200
        geojson_data = response.json() #parse to GEOJSON correctly cuz api is GEOJSON format
        features = geojson_data.get('features', [])
            
        if not features:
            fetching = False
            break
                
        print(f"Successfully downloaded rows {offset} to {offset + len(features)}...")

        #EXTRACT PROPERTIES w/ spatial coords
        for feature in features:
            props = feature.get('attributes', {}).copy()
            geom = feature.get('geometry', {})
            
            #bcuz GeoJSON stores corrds as an array [longitude, latitude]
            if geom:
                props['X'] = geom.get('x') #maps Longitude
                props['Y'] = geom.get('y') #maps Latitude
            else:
                props['X'] = None
                props['Y'] = None            
            records.append(props)

        offset += len(features)
        if len(features) < batch_size:
            fetching = False
    else:
        print(f"Extraction failed at offset {offset}. Status code: {response.status_code}")
        fetching = False

datafile = pd.DataFrame(records) #convert to pandas df
print(f"\nExtraction Loop Finished! Total Rows Gathered: {len(datafile)}")
date_columns = ['APPLICATION_DATE', 'ISSUE_DATE', 'FINAL_DATE', 'EXTRACTION_DATE']
    
for col in date_columns:
    if col in datafile.columns:
        datafile[col] = pd.to_numeric(datafile[col], errors='coerce') #Force the column to be numeric (fixes string-enclosed milliseconds)
            
        datafile[col] = pd.to_datetime(datafile[col], unit='ms', errors='coerce') #Convert millisecond timestamp to proper pandas datetime format
        datafile[col] = pd.to_datetime(datafile[col].dt.date) #STRIP the TIMESTAMP to keep year-month-day only, no time

#LOAD
    #create an explicit mapping dictionary for SQLAlchemy
datafile.to_sql('kitchener_buildings_permits', engine, if_exists='replace', index=False, chunksize=10000, method='multi') ##created a brand-new table named kw_building_permits inside my PostgreSQL database and filled it with data
print("All historical rows successfully pushed to PostgreSQL database!")


# %%
#TRANSFORM
import geopandas as gpd
from shapely.geometry import Point
with open("permits_query.sql", 'r') as file:
    sqlfile = file.read()
clean_file = pd.read_sql(sqlfile, engine)
geometry = [Point(xy) for xy in zip(clean_file['X'], clean_file['Y'])] 
buildings_gdf = gpd.GeoDataFrame(clean_file, geometry=geometry, crs="EPSG:4326") #our geodataframe is now in the correct coordinate reference system (CRS) for UTM zone 17N, which is EPSG:26917. This means that the coordinates are in meters and are suitable for spatial analysis in that region.

# %%
print(buildings_gdf.crs)
print(buildings_gdf['geometry'].head())

# %%
    #load kitchener wards boundary data through a live geojson connection using the geojson link
wards_gdf = gpd.read_file("https://services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/Wards/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson")
wards_gdf = wards_gdf.to_crs("EPSG:4326") #convert the wards geodataframe to the same CRS as our permits data for accurate spatial analysis

buildings_gdf.crs = "EPSG:26917" #tell geopandas that the CRS of our buildings permits geodataframe is in UTM zone 17N (EPSG:26917)
buildings_gdf = buildings_gdf.to_crs("EPSG:4326") #fix the CRS of our buildings permits geodataframe to match the wards geodataframe (EPSG:4326) for accurate spatial analysis

    #perform a WITHIN spatial join to associate each permit with the ward it falls WITHIN
buildings_wards_joined = gpd.sjoin(buildings_gdf, wards_gdf, how="left", predicate="within")

# %%
#since the date columns are in string format, we need to convert them to datetime objects for accurate calculations. We can use the pd.to_datetime() function to do this. The format of the date strings is specified using the date_format variable.
buildings_wards_joined["APPLICATION_DATE"] = pd.to_datetime(buildings_wards_joined["APPLICATION_DATE"])
buildings_wards_joined["ISSUE_DATE"] = pd.to_datetime(buildings_wards_joined["ISSUE_DATE"])

buildings_wards_joined["APPROVAL_DURATION"] = (buildings_wards_joined["ISSUE_DATE"] - buildings_wards_joined["APPLICATION_DATE"]).dt.days
buildings_wards_joined = buildings_wards_joined[buildings_wards_joined["APPROVAL_DURATION"] >= 0] #filter out any negative approval durations, which are likely data entry errors

# %%
#filter out the outlier numbers of approval_duration column (approx 70k falls between 0-200 days, so we get rid of other 1.8k that is higher than 200 days)
bwj_duration_filtered = buildings_wards_joined[buildings_wards_joined["APPROVAL_DURATION"] <= 200] #filter out any approval durations that are greater than 200 days, which are likely outliers or data entry errors

# %%
##group by permit_type & work_type to see the approval duration, as well as simutaneously ignore the outlier values of approval duration
#bwj_duration_filtered.groupby("WORK_TYPE_CLEAN")["APPROVAL_DURATION"].mean().sort_values(ascending=False) ##groupby() followed by .mean() calculates the average approval duration for each unique permit type

#create a final_year col to calcualte the project duration from issue year to final year
bwj_duration_filtered["FINAL_YEAR"] = pd.to_datetime(bwj_duration_filtered["FINAL_DATE"]).dt.year
bwj_duration_filtered = bwj_duration_filtered[bwj_duration_filtered["FINAL_YEAR"].notna()] #filter out any rows where FINAL_YEAR is null, which indicates that the project has not been completed yet
bwj_duration_filtered["PROJECT_DURATION"] = bwj_duration_filtered["FINAL_YEAR"] - bwj_duration_filtered["ISSUE_YEAR"]


#some project duration is negative, which is likely due to data entry errors or missing final dates. We can filter out these negative values to get a more accurate representation of project durations.
#bwj_duration_filtered.loc[bwj_duration_filtered["PROJECT_DURATION"] < 0, ["ISSUE_YEAR", "FINAL_YEAR", "PROJECT_DURATION"]]
bwj_duration_filtered = bwj_duration_filtered[bwj_duration_filtered["PROJECT_DURATION"] >= 0] #filter out any negative project durations, which are likely data entry errors or missing final dates
bwj_duration_filtered.groupby("PERMIT_TYPE_CLEAN")["PROJECT_DURATION"].mean().sort_values(ascending=False)

#turn one of my x var into a categorical variable by turning it into a string
buildings_wards_joined["APPLICATION_MONTH"] = buildings_wards_joined["APPLICATION_MONTH"].astype(str)

# %%
buildings_wards_joined = buildings_wards_joined[buildings_wards_joined["APPROVAL_DURATION"] <= 60] #filter out any approval durations that are greater than 200 days, which are likely outliers or data entry errors
buildings_wards_joined = buildings_wards_joined[buildings_wards_joined["CONSTRUCTION_VALUE_CLEAN"] <= 4000000]
buildings_wards_joined = buildings_wards_joined[buildings_wards_joined["APPLICATION_DATE"].dt.year >= 2016] #reduced to 26k rows

# %%
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

#FIRST split data into train, validation, and test sets CHRONOLOGICALLY, so that the model is trained on past data and tested on future data. This is important for time series data, as we want to avoid data leakage and ensure that the model is evaluated on unseen data.
modeling_bwj = buildings_wards_joined.sort_values(by="APPLICATION_DATE").reset_index(drop=True) #sort the data by application date to ensure that the train, validation, and test sets are split chronologically

    #split the data into 70% train, 15% validation, and 15% test sets
total_rows = len(modeling_bwj)
train_size = int(total_rows * 0.7)
val_size = int(total_rows * 0.15)
test_size = total_rows - train_size - val_size

train_data = modeling_bwj.iloc[:train_size]
val_data = modeling_bwj.iloc[train_size:train_size + val_size]
test_data = modeling_bwj.iloc[train_size + val_size:]

x_cols = ['APPLICATION_MONTH', 'PERMIT_TYPE_CLEAN', 'WORK_TYPE_CLEAN', 'WARD', 'CONSTRUCTION_VALUE_CLEAN']
x_train = train_data[x_cols]
x_val = val_data[x_cols]

    #log transform our continuous y right away 
y_train = train_data["APPROVAL_DURATION"]
y_val = val_data["APPROVAL_DURATION"]


#SECOND: ML PIPELINES w/ ONEHOTENCODER & COLUMNTRANSFORMER FOR CONTINUOUS AND CATEGORICAL X VARS
continuous_x = ['CONSTRUCTION_VALUE_CLEAN']
categorical_x = ['PERMIT_TYPE_CLEAN', 'WORK_TYPE_CLEAN', 'WARD', 'APPLICATION_MONTH']

    #log-log transform our continuous x var to reduce skewness, make the distribution more normal, and handle 0s
    #FunctionTransformer converts numpy function into sklearn tool to fit into pipeline
continuous_pipeline = Pipeline(steps=[
    ('scaler', StandardScaler()) #standardize the continuous x var
])

    #onehotencoder turns categorical x vars into binary cols, necessary for regression models
    #drop_first=True avoids multicollinearity by dropping the 1st category of each x categorical variable, ignore unknown categories
categorical_pipeline = Pipeline(steps=[
    ('onehot', OneHotEncoder(drop='first', handle_unknown = 'ignore', sparse_output=False)) #sparse_output=False returns a dense array instead of a sparse matrix, which is easier to work with in pandas and sklearn
])

    #combine continuous & categorical pipelines into a single column transformer, which applies the appropriate transformations to each type of x variable
preprocessor = ColumnTransformer(transformers=[
    ('continuous', continuous_pipeline, continuous_x),
    ('categorical', categorical_pipeline, categorical_x)
])

    #FINAL UNIFIED pipeline that combines the preprocessor with a tree model, which will be trained on the transformed x variables and the log-transformed y variable
tree_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('model', HistGradientBoostingRegressor())
])


#THIRD: EXECUTE THE PIPELINE ON TRAINING DATA

    #fit the pipeline on the training data, which trains the tree model on the transformed x variables and the log-transformed y variable
tree_pipeline.fit(x_train, y_train)

# Predict raw days directly (no expm1 needed)
y_val_pred_days = tree_pipeline.predict(x_val)

# Enforce non-negative days if model predicts below zero
y_val_pred_days = np.maximum(y_val_pred_days, 0)
y_val_actual_days = y_val  # already raw

# %%
print("Max Actual Days:", y_val_actual_days.max())
print("Max Predicted Days:", y_val_pred_days.max())
# first check showed Max Actual Days: 1673.0000000000002
# Max Predicted Days: 234.76802882192035
# this shows that model blind to long-running permits. 
# #It is severely underestimating the variance of your target variable, 
# which is exactly why your R^2 score is negative


# %%
#FOURTH: EVALUATE THE MODEL PERFORMANCE

mae = mean_absolute_error(y_val_actual_days, y_val_pred_days)
rmse = root_mean_squared_error(y_val_actual_days, y_val_pred_days)
r2 = r2_score(y_val_actual_days, y_val_pred_days)

n = x_val.shape[0]  # Number of observations
p = x_val.shape[1]  # Number of predictors
adjusted_r2 = 1 - ((1 - r2) * (n - 1) / (n - p - 1))

print("--- MODEL METRICS ---")
print(f"Validation R2: {r2:.4f}")
print(f"Validation Adjusted R2: {adjusted_r2:.4f}")
print(f"Validation Mean Absolute Error (MAE):   {mae:.2f} Days")
print(f"Validation Root Mean Squared Error:     {rmse:.2f} Days")



