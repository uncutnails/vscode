**Hypothesis #1: Permit Bureaucracy Bottleneck (Processing Delays)**
The Problem: Unreasonable delays between submitting an application and getting approval hold up housing construction. Measuring exactly where these delays happen can pinpoint municipal inefficiency.
**APPLICATION DATE to ISSUE DATE:** Calculate the duration (in days) to see how long it takes for a permit to get approved.
**ISSUED BY & WORK TYPE:** Group the data to see which municipal departments or specific permit types (e.g., Residential vs. Commercial) experience the longest wait times.
**APPLICATION DATE to FINAL DATE:** Measure the absolute lifespan of a construction project from its first submission to final sign-off.

**Multiple Linear Regression model, Chronological Train-Validation-Test Split (60% / 20% / 20%).**
### 4. Predictive Machine Learning Extension (Scikit-Learn Pipeline)
*   **The Predictive Goal**: Move from historical reporting to forward-looking resource allocation by predicting total permit processing time (Duration in days) at the exact moment a developer submits an application.
*   **Feature Leakage Prevention Constraints**: 
To maintain strict real-world validity, the feature matrix X is entirely restricted to information known at the municipal intake desk at the exact moment of submission, such as WORK_TYPE, WARD, initial CONSTRUCTION_VALUE, and APPLICATION_MONTH. Any metrics recorded later in the permit lifecycle—such as FINAL_DATE or late-stage inspection remarks—are strictly excluded. This strict boundary prevents data leakage and ensures the model simulates a true production environment capable of forecasting processing delays for newly incoming applications.


Phase 0
~~I imported my CSV file into PostgreSQL database through the pgAdmin app/interface for PostgreSQL. From database, you drop down to schemas, then public, then right click the Table option to create your own table as PostgreSQL requires you to build the empty table structure before you can import a CSV. Define your columns to match your CSV headers~~ 
This is actually a tedious way so i’m going to do it with Python pandas & sqlalchemy to automatically create the table and load the data into PostgreSQL!

Sqlalchemy: the bridge to connect to PostgreSQL.   Address: postgresql+psycopg2://uncutnails:your_password@localhost:port/Building_Permits_KW 
Postgresql is the language we’re connecting to.
Psycopg2 library: Python needs a translator to talk to Postgresql
The data was loaded into Postgresql and I opened the data table in pgadmin$ first, then I switched to opening it in DBeaver using the same tree path: databases, file, schemas, public, then table. 

Data Cleaning with SQL in DBeaver:
1. Duplicates: for this dataset, there's no need to do find fuplicates & remove as it's highly unlikely to contain strict system-level duplicates.
2. Handling NULL values: Work Type & Final Date columns are lots of null values or empty strings. Final Date column makes sense as there exist building construction that are yet to be finish. Work Type has a lot of empty value because municipalities leave this blank for simple projects (i.e. minor renovations) so it often requires manual data entry by the applicant, which leads to missing data. APPLICATOIN DATE & ISSUE DATE & ISSUED BY: these 3 columns have 6 rows affected in total and since these var are important, we'll just filter out those rows. I used COALESE to label nulls in Work Type as 'Unknown' and nulls in Final Date as 'Unfinished'
Construction_Value: Because construction values are highly skewed (lots of small residential projects, a few multi-million dollar developments), you should use the median value to fill in blanks.
3. 
