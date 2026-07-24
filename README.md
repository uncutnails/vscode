Phase 0
~~I imported my CSV file into PostgreSQL database through the pgAdmin app/interface for PostgreSQL. From database, you drop down to schemas, then public, then right click the Table option to create your own table as PostgreSQL requires you to build the empty table structure before you can import a CSV. Define your columns to match your CSV headers~~ 
This is actually a tedious way so i’m going to do it with Python pandas & sqlalchemy to automatically create the table and load the data into PostgreSQL!

Sqlalchemy: the bridge to connect to PostgreSQL.   Address: postgresql+psycopg2://uncutnails:your_password@localhost:port/Building_Permits_KW 
Postgresql is the language we’re connecting to.
Psycopg2 library: Python needs a translator to talk to Postgres 


Data Profiling/Sanity Checking:	
1. Row Count 		2. Primary Key & Duplicates	    3. Completeness Check (Finding NULL Values)
