**Hypothesis #1: Permit Bureaucracy Bottleneck (Processing Delays)**
The Problem: Unreasonable delays between submitting an application and getting approval hold up housing construction. Measuring exactly where these delays happen can pinpoint municipal inefficiency.
**APPLICATION DATE to ISSUE DATE:** Calculate the duration (in days) to see how long it takes for a permit to get approved.
**ISSUED BY & WORK TYPE:** Group the data to see which municipal departments or specific permit types (e.g., Residential vs. Commercial) experience the longest wait times.
**APPLICATION DATE to FINAL DATE:** Measure the absolute lifespan of a construction project from its first submission to final sign-off.

**Multiple Linear Regression model, Chronological Train-Validation-Test Split (60% / 20% / 20%).**
Predictive Machine Learning Extension (Scikit-Learn Pipeline)
*   **The Predictive Goal**: Move from historical reporting to forward-looking resource allocation by predicting total permit processing time (Duration in days) at the exact moment a developer submits an application.
*   **Feature Leakage Prevention Constraints**: 
To maintain strict real-world validity, the feature matrix X is entirely restricted to information known at the municipal intake desk at the exact moment of submission, such as WORK_TYPE, WARD, initial CONSTRUCTION_VALUE, and APPLICATION_MONTH. Any metrics recorded later in the permit lifecycle—such as FINAL_DATE or late-stage inspection remarks—are strictly excluded. This strict boundary prevents data leakage and ensures the model simulates a true production environment capable of forecasting processing delays for newly incoming applications.


Phase 0
~~I imported my CSV file into PostgreSQL database through the pgAdmin app/interface for PostgreSQL. From database, you drop down to schemas, then public, then right click the Table option to create your own table as PostgreSQL requires you to build the empty table structure before you can import a CSV. Define your columns to match your CSV headers~~ 
This is actually a tedious way so i’m going to do it with Python pandas & sqlalchemy to automatically create the table and load the data into PostgreSQL!

Sqlalchemy: the bridge to connect to PostgreSQL.   Address: postgresql+psycopg2://username:your_password@localhost:port/Building_Permits_KW 
Postgresql is the language we’re connecting to.
Psycopg2 library: Python needs a translator to talk to Postgresql
After buidling a postgresql engine to connect & upload the data, I applied it as a parameter to my .to_sql function & it uploaded the kw_building_permits data inside my PostgreSQL database in Dbeaver. I initially opened the data table in pgadmin$ first, but then I realized DBeaver is a more profesionally-used tool instead of pgadmin so I switched to opening it in DBeaver using the same tree path in pgadmin: databases, file, schemas, public, then table. 
Now can I begin to do some data cleaning.

**Data Cleaning with SQL in DBeaver:** permits.sql
1. Duplicates: for this dataset, there's no need to do find fuplicates & remove as it's highly unlikely to contain strict system-level duplicates.
2. Handling NULL values: Work Type & Final Date columns are lots of null values or empty strings. Final Date column makes sense as there exist building construction that are yet to be finish. Work Type has a lot of empty value because municipalities leave this blank for simple projects (i.e. minor renovations) so it often requires manual data entry by the applicant, which leads to missing data. APPLICATOIN DATE & ISSUE DATE & ISSUED BY: these 3 columns have 6 rows affected in total and since these var are important, we'll just filter out those rows. I used COALESE to label nulls in Work Type as 'Unknown' and nulls in Final Date as 'Unfinished'
Construction_Value: Because construction values are highly skewed (lots of small residential projects, a few multi-million dollar developments), I used the median value to fill in blanks. I found the median value through using 2 CTE.

**Bringing back to Jupyter Notebook:**
To bring my cleaned data in DBeaver back into my VsCode JupyterNotebook, I made sure that my permits.sql's file path would point to the same location in vscode in order for the sql file to also appear in vscode. Once I refreshed & the permits.sql appeared in VSCODE, I read the file the with open & read method & saved the file to a variable, and finally saved it as a clean_file var using .read_sql() with the engine as a parameter to connect & request the data. 
I replaced the original columns with misisng data (work type, application date, construction value) with the cleaned ones that I cleaned in PosgreSQL, then I dropped the cleaned cols & the index_right col (the row numbers col).
*  _Data engineering a WARD col:_
I imported geopandas & shapely.geometry's Point object. I used these two libraries to engineer a WARD column using Kitchener's Ward Boundary data from a live GEOJSON link (this is because I realized I could not download the GEOJSON file as it was taking forever so I restorted to using a GEOJSON link). First, using the Point funciton form the shapely.geometry library, I built a list of shapely Point objects from the x and y coords in the clean_file. The x & y coords were in EPSG:26917, a unique code for UTM Zone 17N, a spatial reference system used to map locations on Earth. Each Point represents the location of a building permit. Then, I used this list create a geodataframe with the correct corrd reference system (CRS) for UTM zone 17N, which is EPSG:26917. Second, I uploaded the Kitchener Wards data into a geodataframe & converted it to the same CRS as our permits data for accurate spatial analysis. Then, I perform a WITHIN spatial join to associate each permit with the ward it falls WITHIN. I now have a WARD (str col) and a WARDID (int col) in which both's daa are numbers.
*  _Pinpointing the municipal inefficiency:_

