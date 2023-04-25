# Testing Setup Instructions

```
- Navigate inside sabatini-datajoint-pipeline/ while in sabatini-datajoint conda environment
- Rerun editable installation of codebase to make sure that most updated local code is run

    pip install -e .

- Launch ipython (type ipython into terminal) after (cd sabatini-datajoint-pipeline/) or  
- Navigate to a jupyter notebook that is configured with the updated conda environment

Next, import the necessary modules from the pipeline:

    from workflow.pipeline import *

- Now that variables have been defined, you should see the database schemas present, can verify by displaying the session.Session() table. 
- Define the key of interest: If you are testing insertion of a new subject with a new type of data format you can do this by inserting into subject.Subject(), session.Session(), and session.SessionDirectory() tables. To obtain the session_key, you can run
    
    session_key = (session.Session() & 'subject="SUBJECT_NAME").fetch1("KEY")

- Using this session_key, you can query any specific table that you want to test code on,

    photometry_key = (photometry.FiberPhotometry.key_source & session_key) 

- Using this key of interest, you can move to testing the make function of the table that you wish to modify. For example, to test any updates to the photometry.FiberPhotometry() function, you can manually rerun the .populate() function with the key specified. If there are errors in the code and you want to debug to see where the issue is, you should set the python debugger to be active (%pdb on), that way you can step into the make method and rerun the lines of code previous to that which has errored in order to determine what the issue is. 
- This testing can be performed without the python debugger if that is easier. To do this, within the ipython/jupyter environment(where you are running the testing), you need to import the specific imports that are necessary to run that function (i.e. in the case of photometry all the imports defined at the top of photometry.py). Then you can manually run line-by-line each line of the specific .make() method that you are modifying in order to see the data you are working with, and verify that the implemented changes work as intended.

    photometry.FiberPhotometry.populate(photometry_key)
    is equivalent to
    photometry.FiberPhotometry.make(photometry.FiberPhotometry(), photometry_key)
```
