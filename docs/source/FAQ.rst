FAQ
===

I have an error in my ``subject/session/session_dir``.
######################################################
Not to worry, we can fix this within the LabBook GUI by seleting ``Update`` on
the selected table or using a jupyter notebook. You can also apply this same logic to 
other tables as well that are manually inserted.

.. literalinclude:: ../helpers/update.txt

I need to delete an entry. How do I do this?
############################################
Only certain users will have the ability to delete entries. If you have this ability, you can
delete entries by querying the database. For example, if I wanted to delete the subject JBW1, I would
run the following code in a jupyter notebook/ipython terminal.

``(subject.Subject & 'subject="JBW1"').delete()``

How do I view the inserted data?
################################
We will soon have an interactive GUI that will allow you to view the data. For now, you can
query the database using the following code in a jupyter notebook/ipython terminal. You must know
the table architecture to do this but after some practice, it'll begin to make sense.

``(session.SessionDirectory & key).fetch1("session_dir")``

