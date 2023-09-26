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

Do I have to run locally, or can I use a cluster like O2?
#########################################################
We now have instructions for running on the cluster! Please visit :doc:`Installation` for more information.

In the photometry pipeline, my calculated carrier frequency is returning zero. What do I do?
############################################################################################
We have set a parameter called points_2_process to 2**14. However, if you have a session that where the recording 
started later than 2**14 points, you may need to edit this paramater to be bigger. You can locally edit demodulation.py in 
line 233 within the calc_carry function.

What is nperseg and how do I set it?
####################################
nperseg (or no_per_segment) is the number of points to use in each block for the FFT. There is also another metric ``noverlap`` that is automatically
set to ``nperseg/2``. You can read more about this in the scipy.spectrogram documentation if you'd like but here is a general rule: 

nperseg is related to your final downsampling frequency. The relationship is as follows:
``downsampling_frequency = sampling_frequency/noverlap``

However, it is unwise to set nsperseg based on the desired downsampling frequency. This is because the lower nsperseg is set, 
the less resolution you will have within your spectrogram. It is best to begin with some default values and then adjust accordingly.

For those acquiring at 2kHz, we recommend beggining with an ``nperseg == 216``. This will result in a final downsampling frequency 
of ``~18.5 Hz``. For those acquiring with a TDT system which has a sampling rate of ``6103.515625 Hz`` we recommend beggining with an
``nperseg = 966``. This will result in a final downsampling frequency of ``~12.6 Hz``.

