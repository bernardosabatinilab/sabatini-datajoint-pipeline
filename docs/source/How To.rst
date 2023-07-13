How To
======

The sabatini-datajoint-pipeline uses `DataJoint for Python <https://datajoint.com/docs/core/datajoint-python/0.14/>`_. 

The workflow is based on relational principles and makes it simple to keep track of the data provenance and to query the data.
If you are new to DataJoint, we recommend getting started by learning about the principles and foundations that make up DataJoint.
More information can be found in the `DataJoint documentation <https://datajoint.com/docs/core/datajoint-python/0.14/concepts/principles/>`_.

Setting up your data directories
#################################

Your data ``/Inbox`` directory structure will need to be set up like the following: 

|
| Subject1
| ├── Session1

|    ├── Imaging
|     ├── scan0
|        ├── 00001.tif
|        ├── 00002.tif
|        └── ...

|    ├── Photometry
|       ├── timeseries*.mat; data.mat; .tdt
|       └── .toml

|    ├── Behavior
|       ├── .toml
|       └── .parquet, .csv

|    ├── Ephys
|       ├── .bin, .lf, .meta

|    ├── dlc_projects
|       └── PROJECT_PATH
|
| ├── Session2
|   └── ...

Note that the ``Subject`` is the top level directory, and all other data types are nested. You do not need to have all data types for each session.


Inserting the Subject, Session, and Session directory
######################################################

To initate the workflow, we will first need to populate the ``Subject``, ``Session``, and ``SessionDirectory`` tables. There are two ways to do this:
1. We can use a jupyter notebook/CLI/iPython terminal
2. We can use the `DataJoint LabBook GUI <https://labbook.datajoint.io/login>`_.

**Let's start with the jupyter notebook/CLI/iPython terminal.** 

.. literalinclude:: ../helpers/insertion.txt

Importantly, your ``Subject``, ``Session``, and ``SessionDirectory`` structure will need to match the directory structure in your ``/Inbox`` directory.

**We can also do this through the DataJoint LabBook GUI.**
1. Go to the `DataJoint LabBook GUI <https://labbook.datajoint.io/login>`_ and login with your credentials.
2. Now, you will be able to view all the schemas available to you on the left hand side. 
3. Navigate to the ``sabatini_dj_subject`` scehma and click on the ``Subject`` table.
4. Click ``Insert`` and fill out the form.
   
.. image:: ../media/subject.png
    :align: center
    :width: 100%
    :alt: subject_insert

5. Then, navigate to the ``sabatini_dj_session`` schema and click on the ``Session`` table.
6. Click ``Insert`` and fill out the form.
   
.. image:: ../media/session.png
    :align: center
    :width: 100%
    :alt: session

7. Lastly, within the ``sabatini_dj_session`` schema, click on the ``SessionDirectory`` table and fill out the form. 
   
.. image:: ../media/session_dir.png
    :align: center
    :width: 100%
    :alt: session_dir

After successful insertion of the ``Subject``, ``Session``, and ``SessionDirectory`` tables, we can then proceed with operating the rest of the pipeline.





