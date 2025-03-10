Next implementation steps
=========================


Adding automatic tests for the dash gui functions
-------------------------------------------------

To apply automatic test to the entire GUI section it is necessary to create a mock ``remote_connection`` object.
This object must be able to imitate the responses normally coming from the server thus allowing the GUI functions to run as normal.

The most challenging of these will most likely be the ``remote_connection.run()`` command, 
as this takes different strings as input and also returns different strings depending on the resulting operation result.

All methods that rely on this remote_connection object should be located in the ``*_calls.py`` files

Once this mock object is created, the tests can be written in the ``test_dash_ui.py`` file.

The mock object should be initilized as a pytest fixture in the ``conftest.py`` file.

The tests should be written in the following format:

.. code-block:: python
    
    def test_gui_function(mock_remote_connection):
        from foo_calls import bar_function

        # Create the GUI object
        test_function = bar_function(remote_connection=mock_remote_connection)
        
        # Run the GUI function
        result = test_function()
        
        # Check the result
        assert result == expected_result



Adding an offline mode for the GUI 
-----------------------------------

The GUI should be able to run in an offline mode. This means that the GUI should be able to run without a connection to the server.
This however is not easy to implement in the current state of the GUI, as the GUI is heavily reliant 
on the server interactions for its functionality.

A decent work around would be to rely on the mock object from 
the  `GUI tests <#adding-automatic-tests-for-the-dash-gui-functions>`_
to implement an object that simply returns **Offline mode** or something similar on all visible outputs or simply leaves tables and menus empty.

This would allow users to at least use the same gui to interact with already downloaded files.

The offline mode should be activated by a command line argument, for example ``--offline``.



Adding additional computation tools apart from ORCA
---------------------------------------------------

For this step the current ``orca.py`` file should serve as a guideline.

To make future implementation easier this tool is designed to work with any module that uses the provided template class from ``template.py``.

This template provides a few basic functions that the work manager uses to interact with the calculation module. 
This allows for basically any computation tool to be used in this library as long as a child class of the template is implemented.

When new tools are added it might be a good idea to pack all tools into a new subfolder for better organization.


Enabling split calculation pipelines
------------------------------------

Currently all nodes in a layer will be performed on all results from the previous layer.
This is not always the desired behavior, as some calculations might be independent of each other.
However setting this type of branching is not really feasible with the current implementation.
For this to work each node would need a direct reference to its linked nodes. For small pipelines this could work as a simple text argument for each node. 
However for the GUI a drag and drop like solution similar to a molecule builder would be preferable. 